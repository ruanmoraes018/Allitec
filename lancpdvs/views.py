import json
import os
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from clientes.models import Cliente
from core.pagamentos.services import PagamentoService
from lancpdvs.models import Caixa, CaixaMovimento, CaixaFechamento
from lancpdvs.forms import CaixaForm
import unicodedata
from django.http import JsonResponse
from pedidos.models import Pagamento, Pedido, PedidoFormaPgto, PedidoProduto
from produtos.models import Produto
from util.permissoes import verifica_permissao
from django.db.models import Q
from filiais.models import Filial, Usuario
from formas_pgto.models import FormaPgto
from decimal import Decimal
from django.db import IntegrityError, DatabaseError, transaction
import re
from django.views.decorators.http import require_POST
from django.utils import timezone
from io import BytesIO
from django.conf import settings
import base64
from produtos.models import CodigoProduto
from PIL import Image
from vendedores.models import Vendedor
from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('lancpdvs.view_caixa')
@login_required
def lista_lancamentos(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    sit = request.GET.get('sit')
    fil = request.GET.get('fil')
    user1 = request.GET.get('user1')
    reg = request.GET.get('reg', '10')
    empresa = request.user.empresa
    caixas = Caixa.objects.filter(vinc_emp=empresa)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        caixas = caixas.filter(terminal__nome__icontains=norm_s).order_by('terminal__nome')
    elif tp == 'cod' and s:
        try: caixas = caixas.filter(codigo__iexact=s).order_by('terminal__nome')
        except ValueError: caixas = Caixa.objects.none()
    if sit and sit != 'Todos': caixas = caixas.filter(situacao=sit)
    if fil: caixas = caixas.filter(vinc_fil_codigo=fil)
    if user1: caixas = caixas.filter(usuario_codigo_local=user1)
    filiais = Filial.objects.filter(vinc_emp=request.user.empresa)
    usuarios = Usuario.objects.filter(empresa=request.user.empresa)
    if reg == 'todos': num_pagina = caixas.count() or 1
    else:
        try: num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError: num_pagina = 10  # Valor padrão
    paginator = Paginator(caixas, num_pagina)
    page = request.GET.get('page')
    caixas = paginator.get_page(page)
    return render(request, 'lancpdvs/lista.html', {'caixas': caixas, 'filiais': filiais, 'usuarios': usuarios, 'user1': user1, 'sit': sit, 's': s, 'tp': tp, 'reg': reg,})

@login_required
def lista_lancamentos_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit(): condicao_busca = Q(nome__icontains=termo_busca) | Q(codigo=termo_busca)
        else: condicao_busca = Q(nome__icontains=termo_busca)
        caixas = Caixa.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': p.codigo, 'text': f"{p.terminal.nome.upper()}"} for p in caixas]
        return JsonResponse({'results': results})
    except Exception as e:
        return JsonResponse({'results': [], 'error': str(e)})
    
@login_required
def add_lancamento(request):
    if not request.user.has_perm('lancpdvs.add_caixa'):
        messages.info(request, 'Você não tem permissão para adicionar caixas.')
        return redirect('/lancpdvs/lista/')
    if request.method == 'POST':
        data = request.POST.copy()
        for key in data:
            if key.startswith('forma_'):
                v = data.get(key)
                if not v or v.strip() == '': data[key] = Decimal('0')
                else:
                    v = re.sub(r'[^\d,.-]', '', v)
                    v = v.replace('.', '').replace(',', '.')
                    try: data[key] = Decimal(v)
                    except: data[key] = Decimal('0')
        form = CaixaForm(data, empresa=request.user.empresa)
        if form.is_valid():
            with transaction.atomic():
                caixa = form.save(commit=False)
                caixa.vinc_emp = request.user.empresa
                caixa.vinc_fil = caixa.terminal.vinc_fil
                caixa.usuario = request.user
                caixa.situacao = 'Aberto'
                caixa.save()
                formas = FormaPgto.objects.filter(vinc_emp=request.user.empresa)
                for forma in formas:
                    valor = form.cleaned_data.get(f'forma_{forma.codigo}') or Decimal('0')
                    if valor > 0: CaixaMovimento.objects.create(caixa=caixa, tipo='Entrada', categoria='Saldo Inicial', forma_pagamento=forma, valor=valor, usuario=request.user)
            messages.success(request, 'Caixa aberto com sucesso!')
            return redirect(f'/lancpdvs/lista/?tp=cod&s={caixa.codigo}')
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> {field.label}: {error}")
            return render(request, 'lancpdvs/add.html', {'form': form, 'error_messages': error_messages})
    else: form = CaixaForm(empresa=request.user.empresa)
    formas = FormaPgto.objects.filter(vinc_emp=request.user.empresa, tipo='A vista', situacao='Ativo').values('codigo', 'descricao')
    return render(request, 'lancpdvs/add.html', {'form': form, 'formas_json': list(formas)})

@login_required
def att_lancamento(request, codigo):
    b = get_object_or_404(Caixa, codigo=codigo, vinc_emp=request.user.empresa)
    form = CaixaForm(instance=b, empresa=request.user.empresa)
    if not request.user.has_perm('lancpdvs.change_caixa'):
        messages.info(request, 'Você não tem permissão para editar caixas.')
        return redirect('/lancpdvs/lista/')
    if request.method == 'POST':
        form = CaixaForm(request.POST, instance=b, empresa=request.user.empresa)
        if form.is_valid():
            b.save()
            next_url = request.POST.get('next') or request.GET.get('next')
            bank = str(b.codigo)
            messages.success(request, 'Caixa atualizado com sucesso!')
            if next_url: return redirect(next_url)
            else: return redirect('/lancpdvs/lista/?tp=cod&s=' + bank)
        else:
            error_messages = []
            for field in form:
                if field.errors: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'lancpdvs/att.html', {'form': form, 'b': b, 'error_messages': error_messages})
    else:
        formas = FormaPgto.objects.filter(vinc_emp=request.user.empresa, situacao='Ativo').values('codigo', 'descricao')
        return render(request, 'lancpdvs/att.html', {'form': form, 'b': b, 'formas_json': list(formas)})

@login_required
def del_lancamento(request, codigo):
    if not request.user.has_perm('lancpdvs.delete_caixa'):
        messages.info(request, 'Você não tem permissão para deletar caixas.')
        return redirect('/lancpdvs/lista/')
    b = get_object_or_404(Caixa, codigo=codigo, vinc_emp=request.user.empresa)
    if b.caixamovimento_set.exists():
        messages.error(request, 'Não é possível deletar este caixa porque existem movimentos associados a ele.')
        return redirect('/lancpdvs/lista/')
    else:   
        b.delete()
        messages.success(request, 'Caixa deletado com sucesso!')
        return redirect('/lancpdvs/lista/')

@login_required
def tela_caixa(request, caixa_id):
    empresa = request.user.empresa
    caixa = get_object_or_404(Caixa, codigo=caixa_id, vinc_emp=empresa, situacao='Aberto')
    formas = FormaPgto.objects.filter(vinc_emp=empresa, situacao='Ativo')
    logo_base64 = None
    logo_path = os.path.join(settings.MEDIA_ROOT, str(caixa.vinc_fil.logo))
    if caixa.vinc_fil.logo and os.path.exists(logo_path):
        with Image.open(logo_path) as img:
            if img.mode in ('RGBA', 'LA'):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            else: img = img.convert("RGB")
            buffer = BytesIO()
            img.save(buffer, format="JPEG")
            logo_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    vendedores = Vendedor.objects.filter(vinc_emp=empresa, situacao='Ativo')
    return render(request, 'lancpdvs/caixa.html', {'caixa': caixa, 'formas_pgto': formas, 'vendedores': vendedores, 'logo_base64': logo_base64})

@login_required
def movimentos_caixa(request, caixa_id):
    try:
        caixa = Caixa.objects.get(codigo=caixa_id, vinc_emp=request.user.empresa)
        movs = caixa.movimentos.select_related('forma_pagamento', 'pedido', 'pedido__cli', 'pedido__vendedor')
        # 🔹 ABERTURA
        abertura_qs = movs.filter(categoria='Saldo Inicial')
        if not abertura_qs.exists():
            abertura = [{"data": caixa.data_abertura, "descricao": "Abertura do caixa", "forma": "-", "valor": float(caixa.saldo_inicial or 0)}]
        else:
            abertura = [{
                "data": m.data_hora, "descricao": m.descricao or "Abertura do caixa", "forma": m.forma_pagamento.descricao if m.forma_pagamento else "-", "valor": float(m.valor)
            } for m in abertura_qs]
        # 🔹 VENDAS
        vendas_qs = movs.filter(categoria='Venda').order_by('pedido_id')
        vendas_dict = {}
        for m in vendas_qs:
            pedido_id = m.pedido_codigo
            if pedido_id not in vendas_dict:
                vendas_dict[pedido_id] = {
                    "pedido_id": pedido_id, "cliente": f"{m.pedido.cli_codigo or '-'} - {getattr(m.pedido.cli, 'fantasia', '-')}",
                    "vendedor": f"{m.pedido.vendedor_codigo or '-'} - {getattr(m.pedido.vendedor, 'fantasia', '-')}", "data": m.pedido.dt_emi, "formas": [], "total": 0
                }
            vendas_dict[pedido_id]["formas"].append({"forma": m.forma_pagamento.descricao if m.forma_pagamento else "-", "valor": float(m.valor)})
            vendas_dict[pedido_id]["total"] += float(m.valor)
        vendas = list(vendas_dict.values())
        from collections import defaultdict
        resumo_temp = defaultdict(lambda: {"id": None, "forma": "", "total": 0})
        for m in vendas_qs:
            fp_id = m.forma_pagamento.codigo if m.forma_pagamento else 0
            resumo_temp[fp_id]["id"] = fp_id
            resumo_temp[fp_id]["forma"] = (m.forma_pagamento.descricao if m.forma_pagamento else "-")
            resumo_temp[fp_id]["total"] += float(m.valor)
        resumo_vendas = list(resumo_temp.values())
        total_vendas = float(vendas_qs.aggregate(total=Sum('valor'))['total'] or 0)
        # 🔹 ENTRADAS
        entradas_qs = movs.filter(tipo='Entrada').exclude(categoria='Venda')
        entradas = [{"descricao": m.descricao or "-", "forma": m.forma_pagamento.descricao if m.forma_pagamento else "-", "valor": float(m.valor)} for m in entradas_qs]
        resumo_entradas = entradas_qs.values('forma_pagamento__descricao').annotate(total=Sum('valor'))
        resumo_entradas = [{"forma": r['forma_pagamento__descricao'], "total": float(r['total'])} for r in resumo_entradas]
        total_entradas = float(entradas_qs.aggregate(total=Sum('valor'))['total'] or 0)
        # 🔹 SAÍDAS
        saidas_qs = movs.filter(tipo='Saída')
        saidas = [{"descricao": m.descricao or "-", "forma": m.forma_pagamento.descricao if m.forma_pagamento else "-", "valor": float(m.valor)} for m in saidas_qs]
        resumo_saidas = saidas_qs.values('forma_pagamento__descricao').annotate(total=Sum('valor'))
        resumo_saidas = [{"forma": r['forma_pagamento__descricao'], "total": float(r['total'])} for r in resumo_saidas]
        total_saidas = float(saidas_qs.aggregate(total=Sum('valor'))['total'] or 0)
        # 🔹 TOTAL GERAL
        total_geral = movs.values('forma_pagamento__descricao').annotate(total=Sum('valor'))
        total_geral = [{"forma": t['forma_pagamento__descricao'], "total": float(t['total'])} for t in total_geral]
        valor_total_geral = float(movs.aggregate(total=Sum('valor'))['total'] or 0)
        return JsonResponse({
            "abertura": abertura, "vendas": vendas, "resumo_vendas": resumo_vendas, "total_vendas": total_vendas, "entradas": entradas, "resumo_entradas": resumo_entradas,
            "total_entradas": total_entradas, "saidas": saidas, "resumo_saidas": resumo_saidas, "total_saidas": total_saidas, "total_geral": total_geral, "valor_total_geral": valor_total_geral,
        })
    except Exception as e: return JsonResponse({"erro": str(e)}, status=500)

def buscar_produto(codigo, empresa):
    codigo = str(codigo).strip()
    # 1. Prioridade: código secundário
    cod_sec = CodigoProduto.objects.filter(codigo=codigo, vinc_emp=empresa).select_related('produto').first()
    if cod_sec:
        return cod_sec.produto
    # 2. Fallback: ID do produto
    try: return Produto.objects.get(codigo=int(codigo), vinc_emp=empresa)
    except (ValueError, Produto.DoesNotExist): raise Produto.DoesNotExist("Produto não encontrado")

@login_required
@require_POST
@transaction.atomic
def finalizar_venda(request):
    try:
        data = json.loads(request.body)
        caixa_id = data.get('caixa_id')
        itens = data.get('itens', [])
        pagamentos_front = data.get('pagamentos', [])
        cliente_id = data.get('cliente_id')
        vendedor_id = data.get('vendedor_id')
        tabela_preco_id = data.get('tabela_preco_id')
        cliente = None
        if cliente_id:
            cliente = Cliente.objects.filter(codigo=cliente_id, vinc_emp=request.user.empresa).first()
        if not caixa_id:
            return JsonResponse({'erro': 'Caixa não informado'}, status=400)
        caixa = Caixa.objects.select_for_update().get(codigo=caixa_id, vinc_emp=request.user.empresa)
        if caixa.situacao != 'Aberto': return JsonResponse({'erro': 'Caixa fechado'}, status=400)
        if not itens: return JsonResponse({'erro': 'Venda sem itens'}, status=400)
        # 🔥 VALIDA FORMAS DE PAGAMENTO
        for pg in pagamentos_front:
            forma = FormaPgto.objects.get(codigo=pg['forma_id'])
            # 🔥 CLIENTE SOMENTE À VISTA
            if (cliente and cliente.somente_avista and (forma.tipo or '').strip().upper() == 'A PRAZO'): return JsonResponse({'erro': f'Cliente {cliente.fantasia} permite apenas vendas à vista.'}, status=400)
        # 🔥 verifica PIX pendente
        content_type = ContentType.objects.get_for_model(caixa)
        pix_pendente = Pagamento.objects.filter(content_type=content_type, object_id=caixa.codigo, status="pendente").exists()
        # 🔥 CRIA PEDIDO
        pedido = Pedido.objects.create(vinc_emp=request.user.empresa, vinc_fil=caixa.vinc_fil, caixa=caixa, cli_codigo=cliente_id, vendedor_codigo=vendedor_id,
            tabela_preco_codigo=tabela_preco_id, dt_emi=timezone.now(), dt_fat=timezone.now(), situacao='Faturado' if not pix_pendente else 'Aberto'
        )
        total_venda = Decimal('0.00')
        itens_objs = []
        # 🔥 ITENS
        for item in itens:
            codigo = item.get('produto_id')
            prod = buscar_produto(codigo, request.user.empresa)
            qtd = Decimal(str(item['qtd']))
            vl = Decimal(str(item['preco']))
            obj = PedidoProduto(pedido=pedido, produto=prod, quantidade=qtd, vl_unit=vl, codigo_usado=codigo)
            total_venda += obj.subtotal
            itens_objs.append(obj)
        PedidoProduto.objects.bulk_create(itens_objs)
        pedido.total = total_venda
        pedido.save(update_fields=['total'])
        total_pago = Decimal('0.00')
        movimentos = []
        # 🔥 PAGAMENTOS
        for pg in pagamentos_front:
            forma = FormaPgto.objects.get(codigo=pg['forma_id'])
            valor = Decimal(str(pg['valor']))
            total_pago += valor
            # 🔥 PedidoFormaPgto
            PedidoFormaPgto.objects.create(pedido=pedido, forma_pgto=forma, valor=valor)
            # 🔥 Pagamento interno
            gateway = (forma.gateway or "").strip().lower()
            if gateway in ["", "nenhum", "none"]:
                Pagamento.objects.create(vinc_emp=request.user.empresa, origem=pedido, forma_pgto=forma, valor=valor, status='pago')
            # 🔥 Movimento de caixa
            movimentos.append(
                CaixaMovimento(caixa=caixa,pedido=pedido,tipo='Entrada',categoria='Venda',forma_pagamento=forma,valor=valor,descricao=f'Pedido {pedido.codigo}',usuario=request.user)
            )
        CaixaMovimento.objects.bulk_create(movimentos)
        # 🔥 TROCO
        troco = (
            total_pago - total_venda
            if total_pago > total_venda
            else Decimal('0.00')
        )
        pode_vender_sem_estoque = request.user.has_perm('pedidos.vender_sem_estoque_ped')
        # 🔥 BAIXA ESTOQUE
        for item in itens:
            try:
                prod = Produto.objects.get(codigo=item['produto_id'])
                qtd = Decimal(str(item['qtd']))
                if (hasattr(prod, 'estoque_prod') and prod.estoque_prod is not None):  
                    if not pode_vender_sem_estoque and prod.estoque_prod < qtd:
                        return JsonResponse({'erro': f'Estoque insuficiente para o produto {prod.desc_prod}. Disponível: {prod.estoque_prod}!'}, status=400)
                    prod.estoque_prod -= qtd
                    prod.save()
            except Produto.DoesNotExist: pass
        # 🔥 STATUS PAGAMENTO
        if not pix_pendente:
            pedido.atualizar_status_pagamento()
            pedido.save()
        return JsonResponse({'sucesso': True, 'pedido_id': pedido.codigo, 'total': float(total_venda), 'pago': float(total_pago), 'troco': float(troco), 'pix_pendente': pix_pendente})
    except Exception as e: return JsonResponse({'erro': str(e)}, status=500)

@login_required
@require_POST
def gerar_pagamento_caixa(request):
    try:
        data = json.loads(request.body)
        caixa_id = data.get("caixa_id")
        pagamentos_front = data.get("formas", [])
        if not caixa_id: return JsonResponse({"erro": "Caixa não informado"}, status=400)
        caixa = Caixa.objects.get(codigo=caixa_id, vinc_emp=request.user.empresa)
        if caixa.situacao != "Aberto": return JsonResponse({"erro": "Caixa fechado"}, status=400)
        if not pagamentos_front: return JsonResponse({"erro": "Nenhuma forma enviada"}, status=400)
        # 🔥 remove PIX pendente antigo (igual pedido)
        from django.contrib.contenttypes.models import ContentType
        Pagamento.objects.filter(content_type=ContentType.objects.get_for_model(caixa), object_id=caixa.codigo, status="pendente").delete()
        pagamentos_gerados = []
        for pg in pagamentos_front:
            forma = FormaPgto.objects.get(codigo=pg["forma"])
            valor = Decimal(str(pg["valor"]))
            gateway = (forma.gateway or "").strip().lower()
            if gateway in ["", "nenhum", "none"]: continue
            try:
                service = PagamentoService(forma)
                result = service.gerar_pagamento(valor=valor, descricao=f"Venda Caixa {caixa.codigo}", email=None, external_reference=str(caixa.codigo))
                if not result: continue
                txid = result.get("id")
                qr_code = result.get("qr_code")
                if not txid or not qr_code: continue
                pagamento = Pagamento.objects.create(
                    vinc_emp=caixa.vinc_emp, content_type=ContentType.objects.get_for_model(caixa), object_id=caixa.codigo, forma_pgto=forma, valor=valor, txid=txid,
                    qr_code=qr_code, qr_base64=result.get("qr_base64"), gateway=forma.gateway, status="pendente"
                )
                pagamentos_gerados.append({"txid": pagamento.txid, "qr_code": pagamento.qr_code, "qr_base64": pagamento.qr_base64, "valor": str(pagamento.valor)})
            except Exception: continue
        return JsonResponse({"pagamentos": pagamentos_gerados})
    except Exception as e: return JsonResponse({"erro": str(e)}, status=500)
    
@login_required
def status_pagamento_caixa(request, caixa_id):
    try:
        caixa = Caixa.objects.get(codigo=caixa_id, vinc_emp=request.user.empresa)
        pagamentos = Pagamento.objects.filter(content_type=ContentType.objects.get_for_model(caixa), object_id=caixa.codigo)
        if not pagamentos.exists(): return JsonResponse({"status": "sem_pagamento"})
        # 🔥 se qualquer um ainda estiver pendente
        if pagamentos.filter(status="pendente").exists(): return JsonResponse({"status": "pendente"})
        # 🔥 todos pagos
        if pagamentos.filter(status="pago").exists(): return JsonResponse({"status": "pago"})
        return JsonResponse({"status": "desconhecido"})
    except Caixa.DoesNotExist: return JsonResponse({"erro": "Caixa não encontrado"}, status=404)