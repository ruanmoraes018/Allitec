from datetime import datetime, time
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from formas_pgto.models import FormaPgto
from util.permissoes import verifica_permissao, verifica_alguma_permissao
import json
from django.conf import settings
from PIL import Image
from decimal import Decimal
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import permission_required
from filiais.models import Filial, Usuario
from .models import Pedido, PedidoFormaPgto, PedidoProduto, Pagamento
from clientes.models import Cliente
from produtos.models import Produto
from .forms import PedidoForm
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from core.pagamentos.fluxo import gerar_pagamentos_pedido
from core.pagamentos.services import PagamentoService
from pedidos.models import Pedido
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from contas_receber.models import ContaReceber
import logging
logger = logging.getLogger(__name__)

def parse_decimal(value):
    if value is None or value == "":
        return Decimal("0")
    try:
        # substitui vírgula por ponto antes de converter
        return Decimal(str(value).replace(",", "."))
    except InvalidOperation:
        return Decimal("0")

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
    reg = request.GET.get('reg', '10')
    hoje = datetime.today()
    inicio_dia = datetime.combine(hoje, time.min)
    fim_dia = datetime.combine(hoje, time.max)
    empresa = request.user.empresa
    pedidos = Pedido.objects.filter(vinc_emp=empresa).prefetch_related("itens__produto")
    if s:
        pedidos = pedidos.filter(id__iexact=s).order_by('id')
    # Filtro por data
    if por_dt == 'Sim' and dt_ini and dt_fim:
        try:
            # Converter as datas de pedido de string para date
            dt_ini_dt = datetime.combine(datetime.strptime(dt_ini, '%d/%m/%Y').date(), time.min)
            dt_fim_dt = datetime.combine(datetime.strptime(dt_fim, '%d/%m/%Y').date(), time.max)
            if tp_dt == 'Emissão': pedidos = pedidos.filter(dt_emi__range=(dt_ini_dt, dt_fim_dt))
            elif tp_dt == 'Fatura': pedidos = pedidos.filter(dt_fat__range=(dt_ini_dt, dt_fim_dt))
        except ValueError:
            pedidos = Pedido.objects.none()
    # Apenas aplica o filtro do dia atual se nenhum filtro estiver ativo
    filtros_ativos = any([s, f_s, por_dt == 'Sim', cli, tp_dt and tp_dt != 'Todos'])
    if not filtros_ativos:
        pedidos = pedidos.filter(dt_emi__range=(inicio_dia, fim_dia), situacao='Aberto')
    # Filtro por situação
    if f_s and f_s != 'Todos':
        pedidos = pedidos.filter(situacao=f_s)
    # Filtro por cliente
    if cli: pedidos = pedidos.filter(cli_id=cli)
   # Filtro por Filial
    if fil: pedidos = pedidos.filter(vinc_fil_id=fil)
    # Paginação
    if reg == 'todos':
        num_pagina = pedidos.count() or 1
    else:
        try:
            num_pagina = int(reg) if int(reg) > 0 else 10
        except ValueError:
            num_pagina = 10
    paginator = Paginator(pedidos, num_pagina)
    page = request.GET.get('page')
    pedidos = paginator.get_page(page)

    return render(request, 'pedidos/lista.html', {
        'pedidos': pedidos, 's': s, 'fil': fil, 'cli': cli, 'sit': f_s,
        'filiais': Filial.objects.filter(vinc_emp=request.user.empresa),
        'clientes': Cliente.objects.filter(vinc_emp=request.user.empresa),
        'dt_ini': dt_ini, 'dt_fim': dt_fim, 'p_dt': por_dt, 'tp_dt': tp_dt, 'reg': reg,
    })

def pedidos_por_produto(request, produto_id):
    pedidos = PedidoProduto.objects.filter(produto_id=produto_id, vinc_emp=request.user.empresa).select_related('pedido', 'pedido__cliente')

    data = []
    for ep in pedidos:
        pedido = ep.pedido
        data.append({
            'pedido_id': pedido.id,
            'data': pedido.dt_ent.strftime('%d/%m/%Y') if pedido.dt_ent else '',
            'cliente': str(pedido.cli),  # converte para string
            'quantidade': float(ep.quantidade),
            'valor_unitario': Decimal(ep.vl_unit),
            'total_pedido': float(pedido.total),  # 👈 total da pedido
        })

    return JsonResponse({'pedidos': data})

@login_required
def add_pedido(request):
    # Verifica se o usuário tem permissão para adicionar pedidos
    if not request.user.has_perm('pedidos.add_pedido'):
        messages.info(request, 'Você não tem permissão para adicionar pedidos.')
        return redirect('/pedidos/lista/')

    # Se a requisição for do tipo POST (formulário enviado)
    if request.method == "POST":
        # Cria uma instância do formulário com os dados enviados
        form = PedidoForm(request.POST, empresa=request.user.empresa, user=request.user)

        # Valida se o formulário está correto
        if form.is_valid():
            # Cria o objeto pedido sem salvar ainda no banco
            pedido = form.save(commit=False)
            pedido.vinc_emp = request.user.empresa
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
                        if idx not in produtos_dict:
                            produtos_dict[idx] = {}
                        produtos_dict[idx][campo] = value  # Armazena o valor do campo dentro do dicionário

            # Percorre os produtos organizados e os adiciona na pedido
            for dados in produtos_dict.values():
                try:
                    # Busca o produto no banco pelo código
                    produto = Produto.objects.get(pk=dados.get("codigo"), vinc_emp=request.user.empresa)
                except Produto.DoesNotExist:
                    # Se não encontrar, mostra aviso e ignora este produto
                    messages.warning(request, f"Produto {dados.get('produto')} não encontrado e foi ignorado.")
                    continue

                # Cria ou atualiza o produto vinculado à pedido
                PedidoProduto.objects.update_or_create(
                    pedido=pedido,
                    produto=produto,
                    defaults={
                        "vl_unit": parse_decimal(dados.get("preco_unitario")),
                        "quantidade": parse_decimal(dados.get("quantidade")),
                        "desc_acres": parse_decimal(dados.get("desc_acres")),
                        "tp_desc_acres": "Desconto" if dados.get("operacao") == "desconto" else "Acréscimo",
                    },
                )

            # Atualiza o valor total da pedido depois de salvar os produtos
            pedido.total = pedido.atualizar_total()
            pedido.save(update_fields=["total"])

            # Exibe mensagem de sucesso e redireciona para a lista de pedidos
            messages.success(request, f'Pedido gerado com sucesso!')
            return redirect(f'/pedidos/lista/?s={pedido.id}')
        else:
            # Caso o formulário seja inválido, gera mensagens de erro personalizadas
            error_messages = []
            for field in form:
                for error in field.errors:
                    error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")

            # Renderiza novamente a página com os erros
            return render(request, "pedidos/add.html", {
                "form": form,
                'error_messages': error_messages
            })
    else:
        # Se não for POST, apenas cria o formulário vazio
        form = PedidoForm(empresa=request.user.empresa, user=request.user)

    # Renderiza a página com o formulário
    return render(request, "pedidos/add.html", {
        "form": form,
    })


@verifica_alguma_permissao(
    'pedidos.add_pedido',
    'pedidos.change_pedido',
    'pedidos.delete_pedido'
)

@login_required
def att_pedido(request, id):
    # Busca a pedido no banco (ou retorna 404 se não existir)
    pedido = get_object_or_404(Pedido, pk=id, vinc_emp=request.user.empresa)

    # Verifica se o usuário tem permissão de alteração
    if not request.user.has_perm('pedidos.change_pedido'):
        messages.info(request, 'Você não tem permissão para editar pedidos.')
        return redirect('/pedidos/lista/')

    if pedido.situacao in ["Faturado", "Cancelado"]:
        messages.warning(request, f'Pedidos só podem ser editados com Situação em Aberto!')
        return redirect(f'/pedidos/lista/?s={pedido.id}')
    if request.method == "POST":
        # Cria o formulário com os dados enviados e a instância existente
        form = PedidoForm(request.POST, instance=pedido, empresa=request.user.empresa, user=request.user)

        if form.is_valid():
            pedido = form.save(commit=False)
            pedido.save()
            next_url = request.POST.get('next') or request.GET.get('next')
            # Dicionário temporário para os produtos
            produtos_dict = {}
            for key, value in request.POST.items():
                if key.startswith("produtos["):
                    import re
                    m = re.match(r"produtos\[(\d+)\]\[(\w+)\]", key)
                    if m:
                        idx, campo = m.groups()
                        if idx not in produtos_dict:
                            produtos_dict[idx] = {}
                        produtos_dict[idx][campo] = value

            # Atualiza os produtos da pedido
            produtos_ids = []
            for dados in produtos_dict.values():
                try:
                    produto = Produto.objects.get(pk=dados.get("codigo"), vinc_emp=request.user.empresa)
                except Produto.DoesNotExist:
                    messages.warning(request, f"Produto {dados.get('produto')} não encontrado e foi ignorado.")
                    continue

                ep, created = PedidoProduto.objects.update_or_create(
                    pedido=pedido,
                    produto=produto,
                    defaults={
                        "vl_unit": parse_decimal(dados.get("preco_unitario")),
                        "quantidade": parse_decimal(dados.get("quantidade")),
                        "desc_acres": parse_decimal(dados.get("desc_acres")),
                        "tp_desc_acres": "Desconto" if dados.get("operacao") == "desconto" else "Acréscimo",
                    },
                )
                produtos_ids.append(ep.id)

            # Atualiza o total da pedido
            pedido.total = pedido.atualizar_total()
            pedido.save(update_fields=["total"])
            # 🔥 invalida PIX pendente se o valor mudou
            pagamentos_pendentes = pedido.pagamentos.filter(status="pendente")

            for p in pagamentos_pendentes:
                if p.valor != pedido.total:
                    p.status = "cancelado"
                    p.save(update_fields=["status"])

            messages.success(request, f'Pedido atualizado com sucesso!')
            if next_url:
                return redirect(next_url)
            else:
                return redirect(f'/pedidos/lista/?s={pedido.id}')
        else:
            error_messages = []
            for field in form:
                for error in field.errors:
                    error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, "pedidos/att.html", {
                "form": form,
                "pedido": pedido,
                "error_messages": error_messages
            })
    else:
        # Se não for POST, carrega o formulário com os dados da pedido
        form = PedidoForm(instance=pedido, empresa=request.user.empresa, user=request.user)

    return render(request, "pedidos/att.html", {
        "form": form,
        "pedido": pedido,
        "produtos": pedido.itens.all(),
    })

@login_required
def clonar_pedido(request, id):
    # 🔒 Permissão
    if not request.user.has_perm('pedidos.clonar_pedido'):
        messages.warning(request, "Você não tem permissão para clonar pedidos.")
        return redirect('/pedidos/lista/')
    # 🔍 Pedido original
    pedido_origem = get_object_or_404(
        Pedido,
        pk=id,
        vinc_emp=request.user.empresa
    )
    if request.method == "POST":
        # 👉 igual ao add_pedido
        form = PedidoForm(request.POST, empresa=request.user.empresa, user=request.user)
        if form.is_valid():
            pedido = form.save(commit=False)
            pedido.vinc_emp = request.user.empresa
            pedido.situacao = "Aberto"
            pedido.status_pagamento = "pendente"
            pedido.save()
            # 🔁 produtos
            produtos_dict = {}
            import re
            for key, value in request.POST.items():
                if key.startswith("produtos["):
                    m = re.match(r"produtos\[(\d+)\]\[(\w+)\]", key)
                    if m:
                        idx, campo = m.groups()
                        if idx not in produtos_dict:
                            produtos_dict[idx] = {}
                        produtos_dict[idx][campo] = value
            for dados in produtos_dict.values():
                try:
                    produto = Produto.objects.get(
                        pk=dados.get("codigo"),
                        vinc_emp=request.user.empresa
                    )
                except Produto.DoesNotExist:
                    continue
                PedidoProduto.objects.create(
                    pedido=pedido,
                    produto=produto,
                    vl_unit=parse_decimal(dados.get("preco_unitario")),
                    quantidade=parse_decimal(dados.get("quantidade")),
                    desc_acres=parse_decimal(dados.get("desconto")),
                    tp_desc_acres="Desconto" if dados.get("operacao") == "desconto" else "Acréscimo",
                )
            pedido.total = pedido.atualizar_total()
            pedido.save(update_fields=["total"])
            messages.success(request, "Pedido clonado com sucesso!")
            return redirect(f'/pedidos/lista/?s={pedido.id}')
    else:
        # 👉 pré-preenche com dados do pedido original
        form = PedidoForm(
            instance=pedido_origem,
            empresa=request.user.empresa,
            user=request.user
        )
    return render(request, "pedidos/clonar.html", {
        "form": form,
        "produtos": pedido_origem.itens.all(),  # 🔥 isso já resolve tudo
    })

@login_required
def del_pedido(request, id):
    pedido = get_object_or_404(Pedido, pk=id, vinc_emp=request.user.empresa)

    if not request.user.has_perm('pedidos.delete_pedido'):
        messages.info(request, 'Você não tem permissão para deletar pedidos.')
        return redirect('/pedidos/lista/')

    if pedido.situacao != 'Aberto':
        messages.warning(request, 'Pedidos só podem ser deletados com Situação em <i>Aberto</i>!')
        return redirect(f'/pedidos/lista/?s={pedido.id}')

    pedido.delete()
    messages.success(request, f'Pedido deletado com sucesso!')
    return redirect('/pedidos/lista/')

@login_required
@transaction.atomic
def faturar_pedido(request, id):
    empresa = request.user.empresa
    pedido = get_object_or_404(Pedido.objects.select_related('cli', 'vinc_fil', 'vinc_emp').prefetch_related('itens__produto'), pk=id, vinc_emp=empresa)
    if not request.user.has_perm('pedidos.faturar_pedido'):
        messages.error(request, 'Você não tem permissão para faturar pedidos.')
        return redirect('/pedidos/lista/')
    if request.method != 'POST':
        return redirect('/pedidos/lista/')
    if pedido.situacao != 'Aberto':
        messages.warning(request, 'Pedido não pode ser faturado.')
        return redirect(f'/pedidos/lista/?s={pedido.id}')
    dados = json.loads(request.POST.get('dados_pagamento', '[]'))
    parcelas_json = request.POST.get('parcelas_json', '').strip()
    print(f"\n{'='*60}")
    print(f"💳 FATURANDO PEDIDO {pedido.id}")
    print(f"{'='*60}")
    print(f"Dados recebidos: {dados}")
    print(f"Parcelas recebidas: {parcelas_json}")
    if not dados:
        messages.error(request, "Informe ao menos uma forma de pagamento.")
        return redirect(f'/pedidos/lista/?s={pedido.id}')
    total = Decimal('0.00')
    formas_list = []
    tem_forma_com_parcela = False
    tem_gateway = False
    for d in dados:
        forma_id = d.get('forma')
        try:
            valor = Decimal(str(d.get('valor', 0))).quantize(Decimal('0.01'))
        except:
            messages.error(request, "Valor inválido em uma das formas.")
            return redirect(f'/pedidos/lista/?s={pedido.id}')
        if valor <= 0:
            continue
        forma = FormaPgto.objects.filter(id=forma_id, vinc_emp=empresa).first()
        if not forma:
            messages.error(request, f"Forma de pagamento {forma_id} não encontrada.")
            return redirect(f'/pedidos/lista/?s={pedido.id}')
        print(f"   Forma: {forma.descricao} | Valor: R$ {valor} | Gateway: {forma.gateway}")
        if forma.gateway and forma.gateway != "nenhum":
            tem_gateway = True
            print(f"      ⚠️ Esta forma possui gateway: {forma.gateway}")
        if forma.gera_parcelas:
            tem_forma_com_parcela = True
            print(f"      📄 Esta forma gera parcelas")
        formas_list.append({"forma": forma.id, "valor": valor, "parcelas": d.get('parcelas', 1), "dias": d.get('dias', 0)})
        total += valor
    print(f"\n📊 Resumo:")
    print(f"   Total do pedido: R$ {pedido.total}")
    print(f"   Total das formas: R$ {total}")
    print(f"   Tem gateway: {tem_gateway}")
    print(f"   Tem parcelas: {tem_forma_com_parcela}")
    print(f"   Status pagamento: {pedido.status_pagamento}")
    if total != pedido.total:
        messages.error(request, f"Total das formas (R$ {total}) difere do total do pedido (R$ {pedido.total}).")
        return redirect(f'/pedidos/lista/?s={pedido.id}')
    if tem_gateway:
        print("⚠️ Pedido possui gateway. Aguardando confirmação via webhook.")
        # NÃO FATURA AQUI
        return JsonResponse({
            "ok": True,
            "msg": "Pagamento em processamento. Aguarde confirmação."
        })
    parcelas = []
    if tem_forma_com_parcela:
        print(f"\n📄 Processando parcelas...")
        if not parcelas_json:
            messages.error(request, "Parcelas não informadas para forma que gera parcelamento.")
            return redirect(f'/pedidos/lista/?s={pedido.id}')
        try:
            parcelas_data = json.loads(parcelas_json)
        except:
            messages.error(request, "Erro ao processar parcelas.")
            return redirect(f'/pedidos/lista/?s={pedido.id}')
        for idx, item in enumerate(parcelas_data, 1):
            valor_parcela_str = str(item.get('valor', '0')).strip()
            valor_parcela_str = valor_parcela_str.replace('.', '').replace(',', '.') if ',' in valor_parcela_str else valor_parcela_str
            try:
                valor_parcela = Decimal(valor_parcela_str).quantize(Decimal('0.01'))
            except:
                messages.error(request, f"Valor inválido na parcela {idx}.")
                return redirect(f'/pedidos/lista/?s={pedido.id}')
            vencimento_str = item.get('vencimento')
            try:
                if isinstance(vencimento_str, str):
                    vencimento = datetime.strptime(vencimento_str, '%d/%m/%Y').date()
                else:
                    vencimento = vencimento_str
            except:
                messages.error(request, f"Data inválida na parcela {idx}.")
                return redirect(f'/pedidos/lista/?s={pedido.id}')
            parcelas.append({"forma": formas_list[0]['forma'], "numero": (item.get('numero') or f"{pedido.id}/{idx}").upper(), "valor": valor_parcela, "vencimento": vencimento})
            print(f"   Parcela {idx}: {parcelas[-1]['numero']} - R$ {valor_parcela} - Venc: {vencimento}")
    print(f"\n🚀 Chamando finalizar_pedido()...")
    try:
        finalizar_pedido(pedido, formas=formas_list, parcelas=parcelas if tem_forma_com_parcela else None)
        print(f"✅ Pedido {pedido.id} faturado com sucesso!")
        print(f"{'='*60}\n")
        return JsonResponse({"ok": True, "msg": f"Pedido {pedido.id} faturado com sucesso!", "pedido_id": pedido.id, "reload": True})
    except Exception as e:
        print(f"❌ Erro ao finalizar pedido: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f"Erro ao faturar pedido: {str(e)}")
        return redirect(f'/pedidos/lista/?s={pedido.id}')

@require_POST
@login_required
@transaction.atomic
def cancelar_pedido(request, id):
    pedido = get_object_or_404(Pedido.objects.select_related('vinc_emp', 'vinc_fil', 'cli').prefetch_related('itens__produto'), pk=id, vinc_emp=request.user.empresa)
    if not request.user.has_perm('pedidos.cancelar_pedido'):
        messages.info(request, 'Você não tem permissão para cancelar pedidos.')
        return redirect('/pedidos/lista/')
    motivo = request.POST.get('motivo', '').strip()
    if not motivo:
        messages.info(request, 'Motivo do cancelamento é obrigatório!')
        return redirect(f'/pedidos/lista/?s={pedido.id}')
    if pedido.situacao != 'Faturado':
        messages.warning(request, 'Pedido não está faturado ou já foi cancelado.')
        return redirect(f'/pedidos/lista/?s={pedido.id}')
    contas_pagas = ContaReceber.objects.filter(pedido=pedido, vinc_emp=pedido.vinc_emp, vinc_fil=pedido.vinc_fil, situacao='Paga').exists()
    if contas_pagas:
        messages.error(request, 'Não é possível cancelar: existem contas já recebidas.')
        return redirect(f'/pedidos/lista/?s={pedido.id}')
    ContaReceber.objects.filter(pedido=pedido, vinc_emp=pedido.vinc_emp, vinc_fil=pedido.vinc_fil, situacao='Aberta').delete()
    for item in pedido.itens.all():
        produto = item.produto
        produto.estoque_prod = (produto.estoque_prod or 0) + (item.quantidade or 0)
        produto.save(update_fields=["estoque_prod"])
    PedidoFormaPgto.objects.filter(pedido=pedido).delete()
    pedido.situacao = "Cancelado"
    pedido.dt_fat = datetime.now()  # opcional (log de cancelamento)
    pedido.save(update_fields=["situacao", "dt_fat"])
    messages.success(request, f'Pedido {pedido.id} cancelado com sucesso!')
    return redirect(f'/pedidos/lista/?s={pedido.id}')

@login_required
@require_POST
def gerar_pagamento_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, vinc_emp=request.user.empresa)
    if pedido.situacao != "Aberto":
        return JsonResponse({"erro": "Pedido não pode gerar pagamento"})
    if pedido.pagamentos.filter(status="pendente").exists():
        return JsonResponse({"erro": "Já existe pagamento pendente"})
    formas = json.loads(request.POST.get("formas", "[]"))
    PedidoFormaPgto.objects.filter(pedido=pedido).delete()
    for f in formas:
        PedidoFormaPgto.objects.create(pedido=pedido, forma_pgto_id=f["forma"], valor=f["valor"])
    pagamentos = gerar_pagamentos_pedido(pedido)
    data = []
    for p in pagamentos:
        data.append({"txid": p["txid"], "qr_code": p["qr_code"], "qr_base64": p.get("qr_base64"), "valor": str(p["valor"])})
    return JsonResponse({"pagamentos": data})

@login_required
def status_pagamento_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, vinc_emp=request.user.empresa)
    status_anterior = pedido.status_pagamento
    pedido.atualizar_status_pagamento()
    if pedido.status_pagamento != status_anterior:
        pedido.save(update_fields=["status_pagamento"])
        print(f"✅ Status atualizado: {status_anterior} → {pedido.status_pagamento}")
    return JsonResponse({"status": pedido.status_pagamento, "situacao": pedido.situacao})

@login_required
def recuperar_pix_pendente(request, pedido_id):
    pagamento = Pagamento.objects.filter(pedido_id=pedido_id, status="pendente").last()
    if not pagamento:
        return JsonResponse({"erro": True})
    return JsonResponse({"txid": pagamento.txid, "qr_code": pagamento.qr_code, "qr_base64": pagamento.qr_base64, "valor": str(pagamento.valor)})

import mercadopago
from core.pagamentos.webhooks import processar_webhook

@csrf_exempt
def webhook_pedidos(request):
    result = processar_webhook(request)
    if not result:
        return JsonResponse({"ok": True})
    pagamento = Pagamento.objects.filter(txid=result["txid"]).select_related("pedido").first()
    if not pagamento:
        return JsonResponse({"ok": False})
    if pagamento.status == "pago":
        return JsonResponse({"ok": True})
    if result.get("status") == "pago":
        pagamento.status = "pago"
        pagamento.payload = result.get("payload")
        pagamento.dt_pagamento = timezone.now()
        pagamento.save()
        pedido = pagamento.pedido
        pedido.atualizar_status_pagamento()
        pedido.save(update_fields=["status_pagamento"])
        pedido.refresh_from_db()
        if pedido.status_pagamento == "pago" and pedido.situacao == "Aberto":
            finalizar_pedido(pedido)
    return JsonResponse({"ok": True})

@transaction.atomic
def finalizar_pedido(pedido, formas=None, parcelas=None):
    if pedido.situacao == "Faturado":
        return
    for item in pedido.itens.select_related('produto'):
        produto = item.produto
        produto.estoque_prod = (produto.estoque_prod or Decimal('0')) - item.quantidade
        produto.save(update_fields=["estoque_prod"])
    if formas:
        PedidoFormaPgto.objects.filter(pedido=pedido).delete()
        for f in formas:
            PedidoFormaPgto.objects.create(pedido=pedido, forma_pgto_id=f["forma"], valor=f["valor"])
    if parcelas:
        for p in parcelas:
            vencimento = p.get('vencimento')
            if isinstance(vencimento, str):
                vencimento = datetime.strptime(vencimento, '%d/%m/%Y').date()
            ContaReceber.objects.create(vinc_emp=pedido.vinc_emp, vinc_fil=pedido.vinc_fil, cliente=pedido.cli, pedido=pedido, forma_pgto_id=p.get('forma'), num_conta=p.get('numero', '').upper(), valor=Decimal(str(p.get('valor', 0))), data_vencimento=vencimento, situacao='Aberta')
    pedido.status_pagamento = "pago"
    pedido.situacao = "Faturado"
    pedido.dt_fat = timezone.now()
    pedido.save(update_fields=["status_pagamento", "situacao", "dt_fat"])