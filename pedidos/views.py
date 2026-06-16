from datetime import datetime, time
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from formas_pgto.models import FormaPgto
from util.permissoes import verifica_permissao, verifica_alguma_permissao
import json
from decimal import Decimal
from util.parse_decimal import parse_decimal
from django.views.decorators.http import require_POST
from filiais.models import Filial
from vendedores.models import Vendedor
from .models import Pedido, PedidoFormaPgto, PedidoProduto, Pagamento
from clientes.models import Cliente
from produtos.models import CodigoProduto, Produto
from .forms import PedidoForm
from core.pagamentos.fluxo import gerar_pagamentos_pedido
from pedidos.services import finalizar_pedido
from django.db import transaction
from contas_receber.models import ContaReceber
import logging
logger = logging.getLogger(__name__)
from django.utils.timezone import localtime
import re
from django.utils import timezone
from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML, CSS
from util.logo_impressao import img_base64

@verifica_permissao('pedidos.view_pedido')
@login_required
def lista_pedidos(request):
    s = request.GET.get('s')
    f_s = request.GET.get('sit')
    tp_dt = request.GET.get('tp_dt')
    dt_ini = request.GET.get('dt_ini')
    dt_fim = request.GET.get('dt_fim')
    por_dt = request.GET.get('p_dt')
    cli = request.GET.get('cl')
    fil = request.GET.get('fil')
    vend = request.GET.get('vend')
    reg = request.GET.get('reg', '10')
    hoje = datetime.today()
    inicio_dia = datetime.combine(hoje, time.min)
    fim_dia = datetime.combine(hoje, time.max)
    empresa = request.user.empresa
    pedidos = Pedido.objects.filter(vinc_emp=empresa).prefetch_related("itens__produto")
    if s: pedidos = pedidos.filter(codigo__iexact=s).order_by('codigo')
    # Filtro por data
    if por_dt == 'Sim' and dt_ini and dt_fim:
        try:
            dt_ini_dt = datetime.combine(datetime.strptime(dt_ini, '%d/%m/%Y').date(), time.min)
            dt_fim_dt = datetime.combine(datetime.strptime(dt_fim, '%d/%m/%Y').date(), time.max)
            if tp_dt == 'Emissão': pedidos = pedidos.filter(dt_emi__range=(dt_ini_dt, dt_fim_dt))
            elif tp_dt == 'Fatura': pedidos = pedidos.filter(dt_fat__range=(dt_ini_dt, dt_fim_dt))
        except ValueError: pedidos = Pedido.objects.none()
    # Apenas aplica o filtro do dia atual se nenhum filtro estiver ativo
    filtros_ativos = any([s, f_s, por_dt == 'Sim', cli, tp_dt and tp_dt != 'Todos'])
    if not filtros_ativos: pedidos = pedidos.filter(dt_emi__range=(inicio_dia, fim_dia), situacao='Aberto')
    # Filtro por situação
    if f_s and f_s != 'Todos': pedidos = pedidos.filter(situacao=f_s)
    if cli: pedidos = pedidos.filter(cli__codigo=cli)
    if fil: pedidos = pedidos.filter(vinc_fil__codigo=fil)
    if vend: pedidos = pedidos.filter(vendedor__codigo=vend)
    # Paginação
    if reg == 'todos': num_pagina = pedidos.count() or 1
    else:
        try: num_pagina = int(reg) if int(reg) > 0 else 10
        except ValueError: num_pagina = 10
    paginator = Paginator(pedidos, num_pagina)
    page = request.GET.get('page')
    pedidos = paginator.get_page(page)
    ped_ab_pg = sum(1 for p in pedidos.object_list if p.situacao == 'Aberto')
    ped_fat_pg = sum(1 for p in pedidos.object_list if p.situacao == 'Faturado')
    ped_canc_pg = sum(1 for p in pedidos.object_list if p.situacao == 'Cancelado')
    # Total da página atual
    tot_ab_pg = sum((p.total or Decimal('0.00')) for p in pedidos.object_list if p.situacao == 'Aberto')
    tot_fat_pg = sum((p.total or Decimal('0.00')) for p in pedidos.object_list if p.situacao == 'Faturado')
    tot_canc_pg = sum((p.total or Decimal('0.00')) for p in pedidos.object_list if p.situacao == 'Cancelado')
    return render(request, 'pedidos/lista.html', {
        'pedidos': pedidos, 's': s, 'fil': fil, 'cli': cli, 'sit': f_s, 'vend': vend,
        'filiais': Filial.objects.filter(vinc_emp=request.user.empresa), 'clientes': Cliente.objects.filter(vinc_emp=request.user.empresa),
        'vendedores': Vendedor.objects.filter(vinc_emp=request.user.empresa), 'tot_ab': tot_ab_pg, 'tot_fat': tot_fat_pg, 'tot_canc': tot_canc_pg,
        'ped_ab': ped_ab_pg, 'ped_fat': ped_fat_pg, 'ped_canc': ped_canc_pg, 'dt_ini': dt_ini, 'dt_fim': dt_fim, 'p_dt': por_dt, 'tp_dt': tp_dt, 'reg': reg,
    })
def pedidos_por_produto(request, produto_id):
    pedidos = PedidoProduto.objects.filter(produto__codigo=produto_id, vinc_emp=request.user.empresa).select_related('pedido', 'pedido__cliente')
    data = []
    for ep in pedidos:
        pedido = ep.pedido
        data.append({
            'pedido_id': pedido.codigo, 'data': pedido.dt_ent.strftime('%d/%m/%Y') if pedido.dt_ent else '', 'cliente': str(pedido.cli), 'quantidade': float(ep.quantidade),
            'valor_unitario': Decimal(ep.vl_unit), 'total_pedido': float(pedido.total),  # 👈 total da pedido
        })
    return JsonResponse({'pedidos': data})

@login_required
def detalhes_pedido_ajax(request, codigo):
    try:
        pedido = get_object_or_404(Pedido.objects.select_related('cli', 'vinc_fil', 'vendedor').prefetch_related('itens__produto__unidProd', 'formas_pgto__forma_pgto', 'pagamentos__forma_pgto'), codigo=codigo, vinc_emp=request.user.empresa)
        itens = []
        contador = 1
        for item in pedido.itens.all():
            itens.append({
                "item": f"{contador:03}", "codigo": item.codigo_usado if item.codigo_usado is not None else item.produto.id, "produto": item.produto.desc_prod,
                "unidade": getattr(item.produto.unidProd, "nome_unidade", ""), "valor_unit": str(item.vl_unit), "qtd": str(item.quantidade), "subtotal": str(item.subtotal),
                "desconto_acrescimo": str(item.valor_desc_real), "tp_desc_acres": item.tp_desc_acres,
            })
            contador += 1
        formas_pgto = [
            {"descricao": f.forma_pgto.descricao, "valor": str(f.valor)}
            for f in pedido.formas_pgto.all()
        ]
        pagamentos = [
            {"forma": p.forma_pgto.descricao, "valor": str(p.valor), "status": p.status, "data": p.dt_pagamento.strftime("%d/%m/%Y %H:%M") if p.dt_pagamento else ""}
            for p in pedido.pagamentos.all()
        ]
        data = {
            "id":pedido.codigo,"cliente":pedido.nome_cli,"filial":pedido.fantasia_fil,"vendedor":str(pedido.nome_vend),"situacao":pedido.situacao,"status_pagamento":pedido.status_pagamento,
            "data_emissao": localtime(pedido.dt_emi).strftime("%d/%m/%Y - %H:%M") if pedido.dt_emi else "", "data_faturamento": localtime(pedido.dt_fat).strftime("%d/%m/%Y - %H:%M") if pedido.dt_fat else "",
            "total": str(pedido.total), "obs": pedido.obs, "itens": itens, "formas_pagamento": formas_pgto, "pagamentos": pagamentos, "motivo": pedido.motivo
        }
        return JsonResponse(data)
    except Pedido.DoesNotExist: return JsonResponse({'error': 'Pedido não encontrado'}, status=404)

def buscar_produto(codigo, empresa):
    codigo = str(codigo).strip()
    # 1. Prioridade: código secundário
    cod_sec = CodigoProduto.objects.filter(codigo=codigo, vinc_emp=empresa).select_related('produto').first()
    if cod_sec: return cod_sec.produto
    # 2. Fallback: ID do produto
    try: return Produto.objects.get(codigo=int(codigo), vinc_emp=empresa)
    except (ValueError, Produto.DoesNotExist): raise Produto.DoesNotExist("Produto não encontrado")

@login_required
def add_pedido(request):
    # Verifica se o usuário tem permissão para adicionar pedidos
    if not request.user.has_perm('pedidos.add_pedido'):
        messages.info(request, 'Você não tem permissão para adicionar pedidos.')
        return redirect('/pedidos/lista/')
    empresa = request.user.empresa
    if not empresa:
        messages.error(request, 'Erro crítico: Seu usuário não está vinculado a nenhuma empresa cadastrada.')
        return redirect('/pedidos/lista/')
    # Se a requisição for do tipo POST (formulário enviado)
    if request.method == "POST":
        # Cria uma instância do formulário com os dados enviados
        form = PedidoForm(data=request.POST, empresa=empresa, user=request.user)
        # Valida se o formulário está correto
        if form.is_valid():
            # Cria o objeto pedido sem salvar ainda no banco
            pedido = form.save(commit=False)
            pedido.vinc_emp = empresa
            dt_emissao = request.POST.get('dt_emi')
            # converte a string em um objeto date
            data = datetime.strptime(dt_emissao, '%d/%m/%Y').date()
            # pega a hora atual
            agora = timezone.localtime()
            # junta a data do formulário com a hora atual
            pedido.dt_emi = datetime.combine(data, agora.time())
            pedido.save()  # Salva a pedido no banco
            # Dicionário para organizar os produtos enviados no POST
            produtos_dict = {}
            # Percorre todos os campos enviados no request.POST
            for key, value in request.POST.items():
                # Verifica se o campo pertence a produtos (produtos[...])
                if key.startswith("produtos["):
                    import re
                    # Extrai índice e campo usando regex → produtos[0][codigo], produtos[0][quantidade], etc.
                    m = re.match(r"produtos\[(\d+)\]\[(\w+)\]", key)
                    if m:
                        idx, campo = m.groups()  # Ex: idx = "0", campo = "codigo"
                        if idx not in produtos_dict: produtos_dict[idx] = {}
                        produtos_dict[idx][campo] = value  # Armazena o valor do campo dentro do dicionário
            # Percorre os produtos organizados e os adiciona na pedido
            agrupa = request.user.filial_user.agrupa_itens  # ou request.user.filial
            itens_existentes = {
                (i.produto__codigo, float(i.vl_unit)): i
                for i in PedidoProduto.objects.filter(pedido=pedido)
            }
            for dados in produtos_dict.values():
                codigo = dados.get("codigo")
                try: produto = buscar_produto(codigo, empresa)
                except Produto.DoesNotExist:
                    messages.warning(request, f"Produto {codigo} não encontrado.")
                    continue
                qtd = parse_decimal(dados.get("quantidade"))
                vl_unit = parse_decimal(dados.get("preco_unitario"))
                desc_acres = parse_decimal(dados.get("valor_desc_real"))
                tp = "Desconto" if dados.get("operacao") == "desconto" else "Acréscimo"
                key = (produto.codigo, float(vl_unit))
                item_existente = itens_existentes.get(key)
                if agrupa and item_existente:
                    item_existente.quantidade += qtd
                    item_existente.save()
                else:
                    novo = PedidoProduto.objects.create(pedido=pedido, produto=produto, vl_unit=vl_unit, quantidade=qtd, desc_acres=desc_acres, tp_desc_acres=tp, codigo_usado=codigo)
                    itens_existentes[key] = novo
            # Atualiza o valor total da pedido depois de salvar os produtos
            pedido.total = pedido.atualizar_total()
            pedido.save(update_fields=["total"])
            # Exibe mensagem de sucesso e redireciona para a lista de pedidos
            messages.success(request, f'Pedido gerado com sucesso!')
            return redirect(f'/pedidos/lista/?s={pedido.codigo}')
        else:
            # Caso o formulário seja inválido, gera mensagens de erro personalizadas
            error_messages = []
            for field in form: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            # Renderiza novamente a página com os erros
            return render(request, "pedidos/add.html", {"form": form, 'error_messages': error_messages})
    else: form = PedidoForm(empresa=empresa, user=request.user)
    # Renderiza a página com o formulário
    return render(request, "pedidos/add.html", {"form": form,})

@verifica_alguma_permissao('pedidos.add_pedido', 'pedidos.change_pedido', 'pedidos.delete_pedido')
@login_required
def att_pedido(request, codigo):
    pedido = get_object_or_404(Pedido, codigo=codigo, vinc_emp=request.user.empresa)
    if not request.user.has_perm('pedidos.change_pedido'):
        messages.info(request, 'Você não tem permissão para editar pedidos.')
        return redirect('/pedidos/lista/')
    if pedido.situacao in ["Faturado", "Cancelado"]:
        messages.warning(request, 'Pedidos só podem ser editados com Situação em Aberto!')
        return redirect(f'/pedidos/lista/?s={pedido.codigo}')
    if request.method == "POST":
        form = PedidoForm(data=request.POST, instance=pedido, empresa=request.user.empresa, user=request.user)
        if form.is_valid():
            pedido = form.save(commit=False)
            dt_emissao = request.POST.get('dt_emi')
            # converte a string em um objeto date
            data = datetime.strptime(dt_emissao, '%d/%m/%Y').date()
            if pedido.dt_emi != data:
                # pega a hora atual
                agora = timezone.localtime()
                # junta a data do formulário com a hora atual
                pedido.dt_emi = datetime.combine(data, agora.time())
            pedido.save()
            next_url = request.POST.get('next') or request.GET.get('next')
            # 🔥 ORGANIZA PRODUTOS
            produtos_dict = {}
            for key, value in request.POST.items():
                if key.startswith("produtos["):
                    m = re.match(r"produtos\[(\d+)\]\[(\w+)\]", key)
                    if m:
                        idx, campo = m.groups()
                        if idx not in produtos_dict: produtos_dict[idx] = {}
                        produtos_dict[idx][campo] = value
            # 🔥 CONFIG
            agrupa = request.user.filial_user.agrupa_itens
            # 🔥 REMOVE ITENS ANTIGOS
            PedidoProduto.objects.filter(pedido=pedido).delete()
            # 🔥 CACHE LOCAL (evita query repetida)
            itens_existentes = {}
            # 🔥 RECRIA ITENS
            for dados in produtos_dict.values():
                codigo = dados.get("codigo")
                try: produto = buscar_produto(codigo, request.user.empresa)
                except Produto.DoesNotExist:
                    messages.warning(request, f"Produto {codigo} não encontrado.")
                    continue
                qtd = parse_decimal(dados.get("quantidade"))
                vl_unit = parse_decimal(dados.get("preco_unitario"))
                desc_acres = parse_decimal(dados.get("valor_desc_real"))
                tp = "Desconto" if dados.get("operacao") == "desconto" else "Acréscimo"
                key = (produto.codigo, float(vl_unit))
                item_existente = itens_existentes.get(key)
                # 🔥 AGRUPAMENTO
                if agrupa and item_existente:
                    item_existente.quantidade += qtd
                    item_existente.save()
                else:
                    novo = PedidoProduto.objects.create(pedido=pedido, produto=produto, vl_unit=vl_unit, quantidade=qtd, desc_acres=desc_acres, tp_desc_acres=tp, codigo_usado=codigo)
                    itens_existentes[key] = novo
            # 🔥 ATUALIZA TOTAL
            pedido.total = pedido.atualizar_total()
            pedido.save(update_fields=["total"])
            # 🔥 CANCELA PIX PENDENTE SE VALOR MUDOU
            pagamentos_pendentes = pedido.pagamentos.filter(status="pendente")
            for p in pagamentos_pendentes:
                if p.valor != pedido.total:
                    p.status = "cancelado"
                    p.save(update_fields=["status"])
            messages.success(request, 'Pedido atualizado com sucesso!')
            if next_url: return redirect(next_url)
            return redirect(f'/pedidos/lista/?s={pedido.codigo}')
        else:
            error_messages = []
            for field in form: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, "pedidos/att.html", {"form": form, "pedido": pedido, "error_messages": error_messages})
    else: form = PedidoForm(instance=pedido, empresa=request.user.empresa, user=request.user)
    return render(request, "pedidos/att.html", {"form": form, "pedido": pedido, "produtos": pedido.itens.all(),})

@login_required
def clonar_pedido(request, codigo):
    if not request.user.has_perm('pedidos.clonar_pedido'):
        messages.warning(request, "Você não tem permissão para clonar pedidos.")
        return redirect('/pedidos/lista/')
    empresa = request.user.empresa
    if not empresa:
        messages.error(request, 'Erro crítico: Seu usuário não está vinculado a nenhuma empresa cadastrada.')
        return redirect('/pedidos/lista/')
    pedido_origem = get_object_or_404(Pedido, codigo=codigo, vinc_emp=empresa)
    if request.method == "POST":
        form = PedidoForm(data=request.POST, empresa=empresa, user=request.user)
        if form.is_valid():
            pedido = form.save(commit=False)
            pedido.vinc_emp = empresa
            pedido.situacao = "Aberto"
            pedido.status_pagamento = "pendente"
            data = pedido.dt_emi.date()
            # Hora atual
            agora = timezone.localtime()
            # Data do formulário + hora atual
            pedido.dt_emi = timezone.make_aware(
                datetime.combine(data, agora.time())
            )
            pedido.save()
            produtos_dict = {}
            for key, value in request.POST.items():
                if key.startswith("produtos["):
                    m = re.match(r"produtos\[(\d+)\]\[(\w+)\]", key)
                    if m:
                        idx, campo = m.groups()
                        produtos_dict.setdefault(idx, {})
                        produtos_dict[idx][campo] = value
            agrupa = request.user.filial_user.agrupa_itens
            itens_existentes = {}
            for dados in produtos_dict.values():
                codigo = dados.get("codigo")
                try: produto = buscar_produto(codigo, empresa)
                except Produto.DoesNotExist: continue
                qtd = parse_decimal(dados.get("quantidade"))
                vl_unit = parse_decimal(dados.get("preco_unitario"))
                desc_acres = parse_decimal(dados.get("valor_desc_real"))
                tp = "Desconto" if dados.get("operacao") == "desconto" else "Acréscimo"
                key = (produto.codigo, float(vl_unit))
                item_existente = itens_existentes.get(key)
                if agrupa and item_existente:
                    item_existente.quantidade += qtd
                    item_existente.save()
                else:
                    novo = PedidoProduto.objects.create(pedido=pedido, produto=produto, vl_unit=vl_unit, quantidade=qtd, desc_acres=desc_acres, tp_desc_acres=tp, codigo_usado=codigo)
                    itens_existentes[key] = novo
            pedido.total = pedido.atualizar_total()
            pedido.save(update_fields=["total"])
            messages.success(request, "Pedido clonado com sucesso!")
            return redirect(f'/pedidos/lista/?s={pedido.codigo}')
    else: form = PedidoForm(instance=pedido_origem, empresa=empresa, user=request.user)
    return render(request, "pedidos/clonar.html", {"form": form, "produtos": pedido_origem.itens.all(),})

@login_required
def del_pedido(request, codigo):
    pedido = get_object_or_404(Pedido, codigo=codigo, vinc_emp=request.user.empresa)
    if not request.user.has_perm('pedidos.delete_pedido'):
        messages.info(request, 'Você não tem permissão para deletar pedidos.')
        return redirect('/pedidos/lista/')
    if pedido.situacao != 'Aberto':
        messages.warning(request, 'Pedidos só podem ser deletados com Situação em <i>Aberto</i>!')
        return redirect(f'/pedidos/lista/?s={pedido.codigo}')
    pedido.delete()
    messages.success(request, f'Pedido deletado com sucesso!')
    return redirect('/pedidos/lista/')

@login_required
@transaction.atomic
def faturar_pedido(request, codigo):
    empresa = request.user.empresa
    pedido = get_object_or_404(Pedido.objects.select_related('cli', 'vinc_fil', 'vinc_emp').prefetch_related('itens__produto'), codigo=codigo, vinc_emp=empresa)
    if not request.user.has_perm('pedidos.faturar_pedido'):
        messages.error(request, 'Você não tem permissão para faturar pedidos.')
        return redirect('/pedidos/lista/')
    if request.method != 'POST':
        return redirect('/pedidos/lista/')
    if pedido.situacao != 'Aberto':
        messages.warning(request, 'Pedido não pode ser faturado.')
        return redirect(f'/pedidos/lista/?s={pedido.codigo}')
    dados = json.loads(request.POST.get('dados_pagamento', '[]'))
    parcelas_json = request.POST.get('parcelas_json', '').strip()
    if not dados: return JsonResponse({"ok": False, "msg": "Informe ao menos uma forma de pagamento."})
    total = Decimal('0.00')
    formas_normais = []
    formas_gateway = []
    tem_forma_com_parcela = False
    for d in dados:
        forma_id = d.get('forma')
        try: valor = Decimal(str(d.get('valor', 0))).quantize(Decimal('0.01'))
        except: return JsonResponse({"ok": False, "msg": "Valor inválido."})
        if valor <= 0: continue
        forma = FormaPgto.objects.filter(codigo=forma_id, vinc_emp=empresa).first()
        if not forma: return JsonResponse({"ok": False, "msg": "Forma não encontrada."})
        obj = {"forma": forma.codigo, "valor": valor, "parcelas": d.get('parcelas', 1), "dias": d.get('dias', 0)}
        if forma.gateway and forma.gateway != "nenhum": formas_gateway.append(obj)
        else: formas_normais.append(obj)
        if forma.gera_parcelas: tem_forma_com_parcela = True
        total += valor
    if total != pedido.total: return JsonResponse({"ok": False, "msg": f"Total das formas (R$ {total}) difere do pedido (R$ {pedido.total})"})
    # 🔹 PARCELAS
    parcelas = []
    if tem_forma_com_parcela:
        if not parcelas_json: return JsonResponse({"ok": False, "msg": "Parcelas não informadas."})
        try: parcelas_data = json.loads(parcelas_json)
        except: return JsonResponse({"ok": False, "msg": "Erro nas parcelas."})
        for idx, item in enumerate(parcelas_data, 1):
            valor_str = str(item.get('valor', '0')).replace('.', '').replace(',', '.')
            valor_parcela = Decimal(valor_str).quantize(Decimal('0.01'))
            vencimento = datetime.strptime(item.get('vencimento'), '%d/%m/%Y').date()
            parcelas.append({"forma": formas_normais[0]['forma'] if formas_normais else None, "numero": f"{pedido.codigo}/{idx}", "valor": valor_parcela, "vencimento": vencimento, "data_emissao": pedido.dt_fat or timezone.now().date()})
    # 🔥 FATURA PARTE NORMAL
    if formas_normais:
        resultado = finalizar_pedido(pedido, formas=formas_normais, parcelas=parcelas if tem_forma_com_parcela else None, parcial=bool(formas_gateway), request=request)
        # 🔥 BLOQUEIO REAL DE ERRO
        if isinstance(resultado, dict) and not resultado.get("ok", True):
            transaction.set_rollback(True)
            return JsonResponse({"ok": False, "msg": resultado["erro"]})
    return JsonResponse({"ok": True, "msg": "Pagamento processado. Aguardando restante." if formas_gateway else "Pedido faturado com sucesso!"})

@require_POST
@login_required
@transaction.atomic
def cancelar_pedido(request, codigo):
    pedido = get_object_or_404(Pedido.objects.select_related('vinc_emp', 'vinc_fil', 'cli').prefetch_related('itens__produto'), codigo=codigo, vinc_emp=request.user.empresa)
    if not request.user.has_perm('pedidos.cancelar_pedido'):
        messages.info(request, 'Você não tem permissão para cancelar pedidos.')
        return redirect('/pedidos/lista/')
    motivo = request.POST.get('motivo', '').strip()
    if not motivo:
        messages.info(request, 'Motivo do cancelamento é obrigatório!')
        return redirect(f'/pedidos/lista/?s={pedido.codigo}')
    if pedido.situacao != 'Faturado':
        messages.warning(request, 'Pedido não está faturado ou já foi cancelado.')
        return redirect(f'/pedidos/lista/?s={pedido.codigo}')
    contas_pagas = ContaReceber.objects.filter(pedido=pedido, vinc_emp=pedido.vinc_emp, vinc_fil=pedido.vinc_fil, situacao='Paga').exists()
    if contas_pagas:
        messages.error(request, 'Não é possível cancelar: existem contas já recebidas.')
        return redirect(f'/pedidos/lista/?s={pedido.codigo}')
    ContaReceber.objects.filter(pedido=pedido, vinc_emp=pedido.vinc_emp, vinc_fil=pedido.vinc_fil, situacao='Aberta').delete()
    for item in pedido.itens.all():
        produto = item.produto
        produto.estoque_prod = (produto.estoque_prod or 0) + (item.quantidade or 0)
        produto.save(update_fields=["estoque_prod"])
    pedido.situacao = "Cancelado"
    pedido.dt_canc = datetime.now()  # opcional (log de cancelamento)
    pedido.motivo = motivo
    pedido.save(update_fields=["situacao", "dt_fat"])
    messages.success(request, f'Pedido {pedido.codigo} cancelado com sucesso!')
    return redirect(f'/pedidos/lista/?s={pedido.codigo}')

# @login_required
# @require_POST
# def gerar_pagamento_pedido(request, pedido_id):
#     import requests
#     import json

#     pedido = get_object_or_404(Pedido, codigo=pedido_id, vinc_emp=request.user.empresa)

#     # 1. Monta o payload exatamente com os seus dados reais
#     url = "https://api.checkout.infinitepay.io/links"
#     headers = {
#         "Content-Type": "application/json",
#         "accept": "application/json"
#     }

#     # Ruan, usei aqui a sua URL exata de webhook que você passou: /pagamentos/webhook/
#     payload = {
#         "handle": "ruan-moraes-9r1",
#         "webhook_url": "https://allitec.pythonanywhere.com/pagamentos/webhook/",
#         "items": [
#             {
#                 "quantity": 1,
#                 "price": int(float(pedido.total) * 100),
#                 "description": f"Pedido {pedido.codigo}"
#             }
#         ]
#     }

#     # 2. Tenta disparar a requisição e captura QUALQUER retorno ou erro
#     try:
#         response = requests.post(url, json=payload, headers=headers, timeout=10)

#         # Devolve o Payload enviado e a resposta da InfinitePay na tela para inspeção
#         return JsonResponse({
#             "erro": f"DEBUG ATIVO - Status da API: {response.status_code}",
#             "payload_enviado": payload,
#             "resposta_api_text": response.text
#         }, status=400) # Força cair no .fail() do JS para exibir o texto

#     except Exception as e:
#         # Se o PythonAnywhere Free bloquear a requisição, vai cair aqui e mostrar o motivo
#         return JsonResponse({
#             "erro": f"Falha de Conexão (Possível bloqueio de conta Free): {str(e)}",
#             "payload_enviado": payload
#         }, status=400)
@login_required
@require_POST
def gerar_pagamento_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, codigo=pedido_id, vinc_emp=request.user.empresa)

    # 🕵️‍♂️ Validação 1: Situação
    if pedido.situacao != "Aberto":
        return JsonResponse({"erro": f"Bloqueado: A situação deste pedido é '{pedido.situacao}' e não 'Aberto'."})

    # 🕵️‍♂️ Validação 2: Pagamento Pendente Duplicado
    if pedido.pagamentos.filter(status="pendente").exists():
        return JsonResponse({"erro": "Bloqueado: Já existe um pagamento PENDENTE para este pedido no banco. Delete-o para testar novamente."})

    formas = json.loads(request.POST.get("formas", "[]"))

    # 🕵️‍♂️ Validação 3: Formas vazias vindas do Front-end
    if not formas:
        return JsonResponse({"erro": "Bloqueado: O seu Front-end enviou uma lista de formas de pagamento vazia. O loop não pôde iniciar."})

    # Se passar por tudo, limpa as formas antigas e continua o fluxo normal
    PedidoFormaPgto.objects.filter(pedido=pedido).delete()

    for f in formas:
        PedidoFormaPgto.objects.create(
            pedido=pedido,
            forma_pgto_id=f["forma"],
            valor=f["valor"]
        )

    pagamentos = gerar_pagamentos_pedido(pedido)

    # Se o loop rodar mas a API da InfinitePay falhar internamente e o fluxo devolver vazio:
    if not pagamentos:
        return JsonResponse({"erro": "O fluxo rodou, mas a função gerar_pagamentos_pedido retornou vazia."})

    data = []
    for p in pagamentos:
        data.append({"txid": p["txid"], "qr_code": p["qr_code"], "qr_base64": p.get("qr_base64"), "valor": str(p["valor"])})
    return JsonResponse({"pagamentos": data})

@login_required
def status_pagamento_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, codigo=pedido_id, vinc_emp=request.user.empresa)
    status_anterior = pedido.status_pagamento
    novo_status = pedido.atualizar_status_pagamento()
    if pedido.status_pagamento != status_anterior:
        pedido.save(update_fields=["status_pagamento"])
    # 🔥 PIX pago → fatura automaticamente
    if (novo_status == "pago" and pedido.situacao == "Aberto"):
        pedido.processar_pagamento(None)
        pedido.situacao = "Faturado"
        pedido.refresh_from_db()
    return JsonResponse({"status": pedido.status_pagamento, "situacao": pedido.situacao})

@login_required
def recuperar_pix_pendente(request, pedido_id):
    pagamento = Pagamento.objects.filter(content_type__model="pedido", object_id=pedido_id, status="pendente").last()
    if not pagamento: return JsonResponse({"erro": True})
    return JsonResponse({"txid": pagamento.txid, "qr_code": pagamento.qr_code, "qr_base64": pagamento.qr_base64, "valor": str(pagamento.valor)})

@login_required
def imprimir_cupom_pedido(request, codigo):
    pedido = get_object_or_404(Pedido, codigo=codigo, vinc_emp=request.user.empresa)
    return render(request, 'pedidos/cupom.html', {'pedido': pedido})

@login_required
def imprimir_pedido(request, codigo):
    pedido = get_object_or_404(Pedido.objects.select_related('cli', 'vendedor', 'vinc_fil', 'vinc_emp', 'caixa', 'tabela_preco').prefetch_related('itens__produto', 'formas_pgto__forma_pgto', 'pagamentos__forma_pgto'), codigo=codigo, vinc_emp=request.user.empresa)
    total_itens = sum(i.subtotal for i in pedido.itens.all())
    total_pago = sum(p.valor for p in pedido.pagamentos.all() if p.status == 'pago')
    lg_emp = img_base64(pedido.vinc_fil.logo.path)
    context = {'pedido': pedido, 'usuario': request.user.first_name, 'data_impressao': timezone.localtime(), 'total_itens': total_itens, 'total_pago': total_pago, 'lg_emp': lg_emp}
    html_string = render_to_string('pedidos/a4.html', context)
    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
    css = CSS(string='''
        @page {
            size: A4;
            margin: 1.2cm 1cm 1.2cm 1cm;
            @bottom-right { content: "Página " counter(page) " de " counter(pages); font-size: 10px; font-weight: bold; }
            @bottom-left { content: "By Allitec Sistemas"; font-size: 10px; font-weight: bold; font-style: italic; }
        }

        body {
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            font-size: 11px;
            color: #222;
            line-height: 1.3;
        }

        /* Cabeçalho */
        .cabecalho { width: 100%; margin-bottom: 20px; }
        .cabecalho td { vertical-align: top; }
        .td-logo { width: 120px; text-align: left; }
        .td-info { width: auto; padding-left: 15px; }
        .td-status { width: 200px; }

        .logo {
            max-width: 120px;
            max-height: 65px;
            object-fit: contain;
            display: block;
        }

        .titulo { font-size: 18px; font-weight: bold; color: #1a1a1a; margin-bottom: 4px; }
        .sub-info { font-size: 10px; color: #555; margin-bottom: 2px; }

        .badge-pedido {
            background-color: #2c3e50;
            color: #ffffff;
            padding: 6px 12px;
            font-size: 13px;
            font-weight: bold;
            display: inline-block;
            text-align: center;
            border-radius: 3px;
        }

        /* Estrutura de Tabelas Padrão */
        table { width: 100%; border-collapse: collapse; }
        .mb { margin-bottom: 18px; }
        .text-right { text-align: right; }
        .text-center { text-align: center; }
        .font-bold { font-weight: bold; }
        .color-muted { color: #666; }
        .italic { font-style: italic; }

        .sem-borda td { border: none; padding: 0; }

        /* Tabelas de Dados (Cliente, Pagamentos, Obs) */
        .table-dados {
            border: 1px solid #e0e0e0;
        }
        .table-dados th {
            background-color: #f8f9fa;
            color: #2c3e50;
            text-align: left;
            font-size: 10px;
            font-weight: bold;
            padding: 6px 8px;
            border-bottom: 2px solid #e0e0e0;
            letter-spacing: 0.5px;
        }
        .table-dados td {
            padding: 8px;
            border: 1px solid #eee;
            vertical-align: top;
        }
        .table-dados .label {
            display: block;
            font-size: 9px;
            color: #777;
            text-transform: uppercase;
            margin-bottom: 2px;
        }
        .table-dados .valor {
            font-size: 11px;
            font-weight: bold;
            color: #111;
        }

        /* Tabela de Itens (Produtos) */
        .table-itens {
            border: 1px solid #dee2e6;
        }
        .table-itens th {
            background-color: #2c3e50;
            color: #ffffff;
            font-size: 10px;
            font-weight: 600;
            padding: 8px;
            text-transform: uppercase;
            border: none;
        }
        .table-itens td {
            padding: 7px 8px;
            border-bottom: 1px solid #eee;
            font-size: 10.5px;
            vertical-align: middle;
        }
        .table-itens tbody tr:nth-child(even) {
            background-color: #fdfdfd;
        }
        .table-itens tbody tr:hover {
            background-color: #f8f9fa;
        }

        /* Bloco de Totais */
        .table-totais {
            border: 1px solid #e0e0e0;
            background-color: #f8f9fa;
        }
        .table-totais td {
            padding: 8px 12px;
            font-size: 11px;
            color: #444;
            border-bottom: 1px solid #eee;
        }
        .table-totais .linha-total-final {
            background-color: #e9ecef;
            font-size: 13px;
            font-weight: bold;
            color: #2c3e50;
        }
        .table-totais .linha-total-final td {
            padding: 10px 12px;
            border: none;
        }

        /* Rodapé Informativo */
        .rodape-info {
            text-align: center;
            font-size: 9.5px;
            color: #666;
            border-top: 1px dashed #ccc;
            padding-top: 8px;
            margin-top: 20px;
            page-break-inside: avoid;
        }
    ''')
    pdf = html.write_pdf(stylesheets=[css])
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = (f'inline; filename="Pedido {pedido.codigo}.pdf"')
    return response