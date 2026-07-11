import json
import os
from datetime import datetime, time
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from clientes.models import Cliente, CreditoCliente
from core.pagamentos.services import PagamentoService
from lancpdvs.models import Caixa, CaixaMovimento, CaixaFechamento
from lancpdvs.forms import CaixaForm
import unicodedata
from django.http import JsonResponse
from pedidos.models import Pagamento, Pedido, PedidoDevolucao, PedidoDevolucaoItem, PedidoFormaPgto, PedidoProduto
from produtos.models import Produto
from util.parse_decimal import parse_decimal
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
from collections import defaultdict

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
    dt_ini = request.GET.get('dt_ini')
    dt_fim = request.GET.get('dt_fim')
    por_dt = request.GET.get('p_dt')
    hoje = datetime.today()
    inicio_dia = datetime.combine(hoje, time.min)
    fim_dia = datetime.combine(hoje, time.max)
    reg = request.GET.get('reg', '10')
    empresa = request.user.empresa
    caixas = Caixa.objects.filter(vinc_emp=empresa)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        caixas = caixas.filter(terminal__nome__icontains=norm_s).order_by('terminal__nome')
    elif tp == 'cod' and s:
        try: caixas = caixas.filter(codigo__iexact=s).order_by('terminal__nome')
        except ValueError: caixas = Caixa.objects.none()
    if por_dt == 'Sim' and dt_ini and dt_fim:
        try:
            dt_ini_dt = datetime.combine(datetime.strptime(dt_ini, '%d/%m/%Y').date(), time.min)
            dt_fim_dt = datetime.combine(datetime.strptime(dt_fim, '%d/%m/%Y').date(), time.max)
            caixas = caixas.filter(data_abertura__range=(dt_ini_dt, dt_fim_dt))
        except ValueError: caixas = Caixa.objects.none()
    filtros_ativos = any([s, tp, sit, por_dt == 'Sim', fil and user1])
    if not filtros_ativos: caixas = caixas.filter(data_abertura__range=(inicio_dia, fim_dia), situacao='Aberto')
    if sit and sit != 'Todos': caixas = caixas.filter(situacao=sit)
    if fil: caixas = caixas.filter(vinc_fil__codigo=fil)
    if user1: caixas = caixas.filter(usuario__codigo_local=user1)
    filiais = Filial.objects.filter(vinc_emp=request.user.empresa)
    usuarios = Usuario.objects.filter(empresa=request.user.empresa)
    if reg == 'todos': num_pagina = caixas.count() or 1
    else:
        try: num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError: num_pagina = 10  # Valor padrão
    paginator = Paginator(caixas, num_pagina)
    page = request.GET.get('page')
    caixas = paginator.get_page(page)
    cx_ab_pg = sum(1 for p in caixas.object_list if p.situacao == 'Aberto')
    cx_fec_pg = sum(1 for p in caixas.object_list if p.situacao == 'Fechado')
    return render(request, 'lancpdvs/lista.html', {'caixas': caixas, 'filiais': filiais, 'usuarios': usuarios, 'user1': user1, 'fil': fil, 'dt_ini': dt_ini, 'dt_fim': dt_fim, 'sit': sit, 'p_dt': por_dt, 's': s, 'tp': tp, 'reg': reg, 'cx_ab': cx_ab_pg, 'cx_fec': cx_fec_pg,})

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
    if (not request.user.has_perm('lancpdvs.caixa_outro_user') and caixa.usuario != request.user):
        messages.error(request, 'Seu usuário não pode realizar lançamentos em caixas de outros usuários!')
        return redirect('lista-lancamentos')
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
def realizar_entrada_caixa(request, caixa_id):
    if request.method != "POST":
        return JsonResponse({"sucesso": False}, status=400)

    try:
        caixa = Caixa.objects.get(
            codigo=caixa_id,
            vinc_emp=request.user.empresa,
            situacao='Aberto'
        )

        forma = FormaPgto.objects.get(
            codigo=request.POST.get('forma_pagamento_entrada'),
            vinc_emp=request.user.empresa
        )

        movimento = CaixaMovimento.objects.create(
            caixa=caixa,
            tipo='Entrada',
            categoria='Suprimento',
            forma_pagamento=forma,
            valor=parse_decimal(request.POST.get('valor')),
            descricao=request.POST.get('descricao'),
            usuario=request.user
        )

        return JsonResponse({
            "sucesso": True,
            "fantasia": movimento.caixa.vinc_fil.fantasia,
            "endereco": movimento.caixa.vinc_fil.endereco,
            "numero": movimento.caixa.vinc_fil.numero,
            "bairro": movimento.caixa.vinc_fil.bairro_fil.nome_bairro,
            "cidade": movimento.caixa.vinc_fil.cidade_fil.nome_cidade,
            "uf": movimento.caixa.vinc_fil.uf.nome_estado,
            "tel": movimento.caixa.vinc_fil.tel,
            "caixa": movimento.caixa.terminal.nome,
            "cod_cx": movimento.caixa.codigo,
            "id": movimento.codigo,
            "tipo": movimento.tipo,
            "categoria": movimento.categoria,
            "forma": forma.descricao,
            "valor": float(movimento.valor),
            "descricao": movimento.descricao,
            "usuario": request.user.first_name,
            "data": timezone.localtime(movimento.data_hora).strftime("%d/%m/%Y %H:%M:%S")
        })

    except Exception as e:
        return JsonResponse({
            "sucesso": False,
            "erro": str(e)
        }, status=500)

@login_required
def realizar_saida_caixa(request, caixa_id):
    if request.method != "POST":
        return JsonResponse({"sucesso": False}, status=400)

    try:
        caixa = Caixa.objects.get(
            codigo=caixa_id,
            vinc_emp=request.user.empresa,
            situacao='Aberto'
        )

        forma = FormaPgto.objects.get(
            codigo=request.POST.get('forma_pagamento_saida'),
            vinc_emp=request.user.empresa
        )

        movimento = CaixaMovimento.objects.create(
            caixa=caixa,
            tipo='Saída',
            categoria='Sangria',
            forma_pagamento=forma,
            valor=parse_decimal(request.POST.get('valor')),
            descricao=request.POST.get('descricao'),
            usuario=request.user
        )

        return JsonResponse({
            "sucesso": True,
            "fantasia": movimento.caixa.vinc_fil.fantasia,
            "endereco": movimento.caixa.vinc_fil.endereco,
            "numero": movimento.caixa.vinc_fil.numero,
            "bairro": movimento.caixa.vinc_fil.bairro_fil.nome_bairro,
            "cidade": movimento.caixa.vinc_fil.cidade_fil.nome_cidade,
            "uf": movimento.caixa.vinc_fil.uf.nome_estado,
            "tel": movimento.caixa.vinc_fil.tel,
            "caixa": movimento.caixa.terminal.nome,
            "cod_cx": movimento.caixa.codigo,
            "id": movimento.codigo,
            "tipo": movimento.tipo,
            "categoria": movimento.categoria,
            "forma": forma.descricao,
            "valor": float(movimento.valor),
            "descricao": movimento.descricao,
            "usuario": request.user.first_name,
            "data": timezone.localtime(movimento.data_hora).strftime("%d/%m/%Y %H:%M:%S")
        })

    except Exception as e:
        return JsonResponse({
            "sucesso": False,
            "erro": str(e)
        }, status=500)

@login_required
@require_POST
def cancelar_movimento_caixa(request, caixa_id, movimento_id):
    try:
        with transaction.atomic():

            movimento = get_object_or_404(
                CaixaMovimento.objects.select_related("caixa"),
                caixa__codigo=caixa_id,
                caixa__vinc_emp=request.user.empresa,
                codigo=movimento_id
            )

            if movimento.caixa.situacao == "Fechado":
                return JsonResponse({
                    "erro": "O caixa já está fechado."
                }, status=400)

            if movimento.situacao == "Cancelado":
                return JsonResponse({
                    "erro": "Este lançamento já foi cancelado."
                }, status=400)

            # Opcional: impedir cancelamento de vendas
            if movimento.categoria == "Venda":
                return JsonResponse({
                    "erro": "Movimentos de venda não podem ser cancelados por esta tela."
                }, status=400)

            movimento.situacao = "Cancelado"
            movimento.save(update_fields=["situacao"])
            tipo = movimento.tipo
            return JsonResponse({
                "sucesso": True,
                "mensagem": f"{tipo} cancelada com sucesso!"
            })

    except Exception as e:
        return JsonResponse({
            "erro": str(e)
        }, status=500)

@login_required
def dados_movimento_caixa(request, caixa_codigo, movimento_codigo):
    try:
        movimento = (
            CaixaMovimento.objects
            .select_related(
                "caixa",
                "forma_pagamento",
                "usuario",
                "caixa__vinc_emp"
            )
            .get(
                caixa__codigo=caixa_codigo,
                caixa__vinc_emp=request.user.empresa,
                codigo=movimento_codigo
            )
        )

        filial = movimento.caixa.vinc_fil

        return JsonResponse({
            "sucesso": True,
            "tipo": movimento.tipo,
            "id": movimento.codigo,
            "cod_cx": movimento.caixa.codigo,
            "caixa": movimento.caixa.terminal.nome,
            "descricao": movimento.descricao,
            "forma": movimento.forma_pagamento.descricao,
            "valor": float(movimento.valor),
            "data": timezone.localtime(
                movimento.data_hora
            ).strftime("%d/%m/%Y %H:%M:%S"),

            "fantasia": filial.fantasia,
            "endereco": filial.endereco,
            "numero": filial.numero,
            "bairro": filial.bairro_fil.nome_bairro,
            "cidade": filial.cidade_fil.nome_cidade,
            "uf": filial.uf.nome_estado,
            "tel": filial.tel,
        })

    except CaixaMovimento.DoesNotExist:
        return JsonResponse({
            "sucesso": False,
            "erro": "Movimento não encontrado."
        }, status=404)

    except Exception as e:
        return JsonResponse({
            "sucesso": False,
            "erro": str(e)
        }, status=500)

@login_required
def movimentos_caixa(request, caixa_id):
    try:
        caixa = Caixa.objects.get(
            codigo=caixa_id,
            vinc_emp=request.user.empresa
        )

        movs = caixa.movimentos.select_related(
            'forma_pagamento',
            'pedido',
            'pedido__cli',
            'pedido__vendedor'
        )

        # ==========================================================
        # ABERTURA
        # ==========================================================
        abertura_qs = movs.filter(categoria='Saldo Inicial')

        if not abertura_qs.exists():
            abertura = [{
                "data": caixa.data_abertura,
                "descricao": "Abertura do caixa",
                "forma": "-",
                "valor": float(caixa.saldo_inicial or 0)
            }]
        else:
            abertura = [{
                "data": m.data_hora,
                "descricao": m.descricao or "Abertura do caixa",
                "forma": m.forma_pagamento.descricao if m.forma_pagamento else "-",
                "valor": float(m.valor)
            } for m in abertura_qs]

        # ==========================================================
        # VENDAS (EXIBIÇÃO)
        # ==========================================================
        vendas_qs = movs.filter(
            categoria='Venda'
        ).order_by('pedido_id')

        vendas_dict = {}

        for m in vendas_qs:
            pedido_id = m.pedido.codigo

            if pedido_id not in vendas_dict:
                vendas_dict[pedido_id] = {
                    "pedido_id": pedido_id,
                    "cliente": f"{getattr(m.pedido.cli, 'codigo', '-') or '-'} - {getattr(m.pedido.cli, 'fantasia', '-')}",
                    "vendedor": f"{getattr(m.pedido.vendedor, 'codigo', '-') or '-'} - {getattr(m.pedido.vendedor, 'fantasia', '-')}",
                    "data": m.pedido.dt_emi,
                    "situacao": m.pedido.situacao,
                    "formas": [],
                    "total": 0,
                    "tem_devolucao": m.pedido.tipo_operacao in ('Troca', 'Devolucao'),
                }

            vendas_dict[pedido_id]["formas"].append({
                "forma": m.forma_pagamento.descricao if m.forma_pagamento else "-",
                "valor": float(m.valor),
                "situacao": m.situacao
            })

            # Apenas para exibição
            vendas_dict[pedido_id]["total"] += float(m.valor)

        vendas = list(vendas_dict.values())

        # ==========================================================
        # VENDAS (TOTAIS)
        # ==========================================================
        vendas_total_qs = movs.filter(
            categoria='Venda',
            situacao='Ativo',
            pedido__situacao='Faturado'
        )

        resumo_temp = defaultdict(
            lambda: {
                "id": None,
                "forma": "",
                "total": 0
            }
        )

        for m in vendas_total_qs:
            fp_id = m.forma_pagamento.codigo if m.forma_pagamento else 0

            resumo_temp[fp_id]["id"] = fp_id
            resumo_temp[fp_id]["forma"] = (
                m.forma_pagamento.descricao
                if m.forma_pagamento else "-"
            )
            resumo_temp[fp_id]["total"] += float(m.valor)

        resumo_vendas = list(resumo_temp.values())

        total_vendas = float(
            vendas_total_qs.aggregate(total=Sum('valor'))['total'] or 0
        )

        # ==========================================================
        # ENTRADAS (EXIBIÇÃO)
        # ==========================================================
        entradas_qs = movs.filter(
            tipo='Entrada',
            categoria='Suprimento'
        ).order_by('forma_pagamento__codigo')

        entradas = [{
            "codigo": m.codigo,
            "descricao": m.descricao or "-",
            "forma": m.forma_pagamento.descricao if m.forma_pagamento else "-",
            "valor": float(m.valor),
            "situacao": m.situacao
        } for m in entradas_qs]

        # ==========================================================
        # ENTRADAS (TOTAIS)
        # ==========================================================
        entradas_total_qs = entradas_qs.filter(
            situacao='Ativo'
        )

        resumo_entradas = [
            {
                "forma": r["forma_pagamento__descricao"],
                "total": float(r["total"])
            }
            for r in entradas_total_qs.values(
                "forma_pagamento__descricao"
            ).annotate(
                total=Sum("valor")
            )
        ]

        total_entradas = float(
            entradas_total_qs.aggregate(total=Sum("valor"))["total"] or 0
        )

        # ==========================================================
        # SAÍDAS (EXIBIÇÃO)
        # ==========================================================
        saidas_qs = movs.filter(
            tipo='Saída',
            categoria='Sangria'
        ).order_by('forma_pagamento__codigo')

        saidas = [{
            "codigo": s.codigo,
            "descricao": s.descricao or "-",
            "forma": s.forma_pagamento.descricao if s.forma_pagamento else "-",
            "valor": float(s.valor),
            "situacao": s.situacao
        } for s in saidas_qs]

        # ==========================================================
        # SAÍDAS (TOTAIS)
        # ==========================================================
        saidas_total_qs = saidas_qs.filter(
            situacao='Ativo'
        )

        resumo_saidas = [
            {
                "forma": r["forma_pagamento__descricao"],
                "total": float(r["total"])
            }
            for r in saidas_total_qs.values(
                "forma_pagamento__descricao"
            ).annotate(
                total=Sum("valor")
            )
        ]

        total_saidas = float(
            saidas_total_qs.aggregate(total=Sum("valor"))["total"] or 0
        )

        # ==========================================================
        # TOTAL GERAL
        # ==========================================================
        totais = defaultdict(float)
        # Vendas faturadas
        for m in vendas_total_qs:
            forma = m.forma_pagamento.descricao if m.forma_pagamento else "-"
            totais[forma] += float(m.valor)

        # Suprimentos
        for m in entradas_total_qs:
            forma = m.forma_pagamento.descricao if m.forma_pagamento else "-"
            totais[forma] += float(m.valor)

        # Sangrias
        for m in saidas_total_qs:
            forma = m.forma_pagamento.descricao if m.forma_pagamento else "-"
            totais[forma] -= float(m.valor)

        total_geral = [
            {
                "forma": forma,
                "total": total
            }
            for forma, total in totais.items()
        ]

        valor_total_geral = (
            float(caixa.saldo_inicial or 0)
            + sum(totais.values())
        )

        return JsonResponse({
            "caixa": caixa.codigo,
            "abertura": abertura,
            "vendas": vendas,
            "resumo_vendas": resumo_vendas,
            "total_vendas": total_vendas,
            "entradas": entradas,
            "resumo_entradas": resumo_entradas,
            "total_entradas": total_entradas,
            "saidas": saidas,
            "resumo_saidas": resumo_saidas,
            "total_saidas": total_saidas,
            "total_geral": total_geral,
            "valor_total_geral": valor_total_geral,
        })

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)

def buscar_produto(codigo, empresa):
    codigo = str(codigo).strip()
    # 1. Prioridade: código secundário
    cod_sec = CodigoProduto.objects.filter(codigo=codigo, vinc_emp=empresa).select_related('produto').first()
    if cod_sec:
        return cod_sec.produto
    # 2. Fallback: ID do produto
    try: return Produto.objects.get(codigo=int(codigo), vinc_emp=empresa)
    except (ValueError, Produto.DoesNotExist): raise Produto.DoesNotExist("Produto não encontrado")

from tabelas_preco.models import TabelaPreco
from django.db import models

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
        
        # 🔥 Pega o código do pedido original que foi usado no modal de devolução (se houver)
        codigo_pedido_origem = data.get('codigo_pedido_origem')

        cliente = None
        vendedor = None
        tabela_preco = None

        if cliente_id:
            cliente = Cliente.objects.filter(codigo=cliente_id, vinc_emp=request.user.empresa).first()
        if vendedor_id:
            vendedor = Vendedor.objects.filter(codigo=vendedor_id, vinc_emp=request.user.empresa).first()
        if tabela_preco_id:
            tabela_preco = TabelaPreco.objects.filter(codigo=tabela_preco_id, vinc_emp=request.user.empresa).first()

        if not caixa_id:
            return JsonResponse({'erro': 'Caixa não informado'}, status=400)

        caixa = Caixa.objects.select_for_update().get(codigo=caixa_id, vinc_emp=request.user.empresa)
        if caixa.situacao != 'Aberto': 
            return JsonResponse({'erro': 'Caixa fechado'}, status=400)
        if not itens: 
            return JsonResponse({'erro': 'Venda/Troca sem itens'}, status=400)

        # 🔥 VALIDA FORMAS DE PAGAMENTO
        for pg in pagamentos_front:
            forma = FormaPgto.objects.get(codigo=pg['forma_id'])
            if (cliente and cliente.somente_avista and (forma.tipo or '').strip().upper() == 'A PRAZO'): 
                return JsonResponse({'erro': f'Cliente {cliente.fantasia} permite apenas vendas à vista.'}, status=400)

        content_type = ContentType.objects.get_for_model(caixa)
        pix_pendente = Pagamento.objects.filter(content_type=content_type, object_id=caixa.codigo, status="pendente").exists()

        # Separa os itens em duas listas (Novas vendas vs Devoluções)
        itens_venda_front = [i for i in itens if not i.get('is_devolucao')]
        itens_devolucao_front = [i for i in itens if i.get('is_devolucao')]

        # 🔥 Validação: devolução precisa do código do pedido de origem
        if itens_devolucao_front and not codigo_pedido_origem:
            return JsonResponse({'erro': 'Código do pedido de origem não informado para a devolução.'}, status=400)

        # Determina o tipo de operação global deste pedido
        tipo_operacao_global = 'Venda'
        if itens_devolucao_front:
            tipo_operacao_global = 'Troca' if itens_venda_front else 'Devolucao'

        # Busca o pedido de origem se houver devolução
        pedido_original = None
        if itens_devolucao_front and codigo_pedido_origem:
            pedido_original = Pedido.objects.filter(codigo=codigo_pedido_origem, vinc_emp=request.user.empresa).first()
            if not pedido_original:
                return JsonResponse({'erro': f'Pedido de origem {codigo_pedido_origem} não encontrado nesta empresa.'}, status=400)

        # 🔥 CRIA O PEDIDO PRINCIPAL (CARRINHO DO CAIXA)
        pedido = Pedido.objects.create(
            vinc_emp=request.user.empresa,
            vinc_fil=caixa.vinc_fil,
            caixa=caixa,
            cli=cliente,
            vendedor=vendedor,
            usuario=caixa.usuario,
            tabela_preco=tabela_preco,
            dt_emi=timezone.localtime(timezone.now()),
            dt_fat=timezone.localtime(timezone.now()),
            tipo_operacao=tipo_operacao_global,
            pedido_origem=pedido_original,
            situacao='Faturado' if not pix_pendente else 'Aberto'
        )

        total_venda = Decimal('0.00')
        itens_objs = []
        
        # Listas para controle de cabeçalho da tabela PedidoDevolucao
        itens_para_devolucao_modelo = []
        total_devolucao_modelo = Decimal('0.00')

        # 🔥 PROCESSAMENTO DOS ITENS (Calculando subtotais positivos e negativos)
        for item in itens:
            codigo_prod = item.get('produto_id')
            prod = buscar_produto(codigo_prod, request.user.empresa)
            
            # Garante sinal correto de quantidade/preço de acordo com a operação
            is_dev = item.get('is_devolucao', False)
            qtd = Decimal(str(abs(item['qtd'])))
            vl = Decimal(str(abs(item['preco'])))

            # Se for devolução, salvamos com valores NEGATIVOS no PedidoProduto para compor o subtotal do carrinho
            qtd_salvar = -qtd if is_dev else qtd

            obj = PedidoProduto(
                pedido=pedido, 
                produto=prod, 
                quantidade=qtd_salvar, 
                vl_unit=vl, 
                codigo_usado=codigo_prod
            )
            
            # O property subtotal da sua classe PedidoProduto calcula (base - desconto), 
            # com quantidade negativa ele computará o subtotal negativo perfeitamente.
            total_venda += obj.subtotal
            itens_objs.append(obj)

            # Se for devolução, prepara a estrutura paralela para a tabela PedidoDevolucao
            if is_dev:
                # Localiza a linha original (PedidoProduto) do pedido que está sendo devolvido
                item_pedido_original_id = item.get('item_pedido_id')
                itens_para_devolucao_modelo.append({
                    'item_pedido_id': item_pedido_original_id,
                    'quantidade': qtd
                })
                total_devolucao_modelo += qtd * vl

        # Salva todos os itens criados no pedido atual
        PedidoProduto.objects.bulk_create(itens_objs)
        pedido.total = total_venda
        pedido.save(update_fields=['total'])

        # 🔥 SE HOUVE ITENS DE DEVOLUÇÃO, CRIA O REGISTRO HISTÓRICO EM 'PedidoDevolucao'
        if itens_para_devolucao_modelo and pedido_original:
            devolucao_obj = PedidoDevolucao.objects.create(
                vinc_emp=request.user.empresa,
                vinc_fil=caixa.vinc_fil,
                pedido=pedido_original,
                cliente=cliente or pedido_original.cli,
                usuario=caixa.usuario,
                tipo=tipo_operacao_global,
                total=total_devolucao_modelo,
                observacao=f"Troca efetuada no Caixa. Pedido atual: {pedido.codigo}"
            )
            
            ult_cod_dev = PedidoDevolucao.objects.filter(vinc_emp=request.user.empresa).aggregate(models.Max('codigo'))['codigo__max'] or 0
            devolucao_obj.codigo = ult_cod_dev + 1
            devolucao_obj.save()

            # Cria os itens da devolução amarrados às linhas do pedido original
            for item_dev in itens_para_devolucao_modelo:
                if not item_dev['item_pedido_id']:
                    # Se por algum motivo o front não enviar o ID do item_pedido, levantamos erro para não quebrar o estoque e o saldo
                    raise ValueError(f"Não foi possível identificar a linha original do item de devolução.")

                PedidoDevolucaoItem.objects.create(
                    devolucao=devolucao_obj,
                    item_pedido_id=item_dev['item_pedido_id'], # Chave primária do PedidoProduto original
                    quantidade=item_dev['quantidade']
                )

        # 🔥 REGISTRO DE PAGAMENTOS OU SOBRA (CRÉDITO)
        total_pago = Decimal('0.00')
        movimentos = []

        # Processa pagamentos enviados pelo front (se o saldo for positivo, o usuário enviará dados aqui)
        for pg in pagamentos_front:
            forma = FormaPgto.objects.get(codigo=pg['forma_id'])
            valor = Decimal(str(pg['valor']))
            total_pago += valor
            
            PedidoFormaPgto.objects.create(pedido=pedido, forma_pgto=forma, valor=valor)
            
            gateway = (forma.gateway or "").strip().lower()
            if gateway in ["", "nenhum", "none"]:
                Pagamento.objects.create(vinc_emp=request.user.empresa, origem=pedido, forma_pgto=forma, valor=valor, status='pago')
            
            movimentos.append(
                CaixaMovimento(caixa=caixa, pedido=pedido, tipo='Entrada', categoria='Venda', forma_pagamento=forma, valor=valor, descricao=f'Pedido/Troca {pedido.codigo}', usuario=request.user)
            )

        # Se o total_venda for NEGATIVO, a empresa deve ao cliente (gerar Crédito)
        if total_venda < 0:
            valor_sobra_credito = abs(total_venda)
            credito = CreditoCliente.objects.create(
                vinc_emp=request.user.empresa,
                vinc_fil=caixa.vinc_fil,
                cliente=cliente or pedido_original.cli,
                pedido_origem=pedido_original or pedido,
                usuario=caixa.usuario,
                valor=valor_sobra_credito,
                saldo=valor_sobra_credito,
                situacao='Aberto',
                observacao=f"Crédito gerado devido à sobra de valor em Troca no caixa. Pedido: {pedido.codigo}"
            )
            ult_cod_cred = CreditoCliente.objects.filter(vinc_emp=request.user.empresa).aggregate(models.Max('codigo'))['codigo__max'] or 0
            credito.codigo = ult_cod_cred + 1
            credito.save()

        CaixaMovimento.objects.bulk_create(movimentos)

        # 🔥 CALCULA O TROCO (Apenas se o total pago em dinheiro superou o total positivo da venda)
        # Se total_venda for negativo, o troco em dinheiro é zero e a sobra já virou crédito acima.
        troco = Decimal('0.00')
        if total_venda > 0 and total_pago > total_venda:
            troco = total_pago - total_venda

        pode_vender_sem_estoque = request.user.has_perm('pedidos.vender_sem_estoque_ped')

        # 🔥 MOVIMENTAÇÃO DINÂMICA DE ESTOQUE (Soma devoluções e Subtrai vendas)
        for item in itens:
            try:
                prod = buscar_produto(item['produto_id'], request.user.empresa)
                qtd = Decimal(str(abs(item['qtd'])))
                is_dev = item.get('is_devolucao', False)

                if hasattr(prod, 'estoque_prod') and prod.estoque_prod is not None:
                    if is_dev:
                        # 🔥 PRODUTO RETORNOU: Soma no estoque
                        prod.estoque_prod += qtd
                    else:
                        # 🔥 PRODUTO FOI VENDIDO: Subtrai no estoque com validação
                        if not pode_vender_sem_estoque and prod.estoque_prod < qtd:
                            return JsonResponse({'erro': f'Estoque insuficiente para o produto {prod.desc_prod}. Disponível: {prod.estoque_prod}!'}, status=400)
                        prod.estoque_prod -= qtd
                    prod.save()
            except Produto.DoesNotExist: 
                pass

        # 🔥 STATUS PAGAMENTO
        if not pix_pendente:
            # Se o total da venda foi negativo, considera-se quitado (gerou crédito)
            if pedido.total <= 0:
                pedido.status_pagamento = 'pago'
            else:
                pedido.atualizar_status_pagamento()
            pedido.save()

        return JsonResponse({
            'sucesso': True, 
            'pedido_id': pedido.codigo, 
            'total': float(total_venda), 
            'pago': float(total_pago), 
            'troco': float(troco), 
            'pix_pendente': pix_pendente
        })

    except Exception as e: 
        return JsonResponse({'erro': str(e)}, status=500)

@login_required
def buscar_pedido_troca_devolucao(request):
    try:
        codigo = request.GET.get("codigo")

        if not codigo:
            return JsonResponse({
                "sucesso": False,
                "erro": "Informe o código do pedido."
            })

        # 🔥 Otimizado: Trocamos "itens__devolucoes" por "itens" 
        # já que faremos a query direta no PedidoDevolucaoItem para evitar o conflito do Django
        pedido = Pedido.objects.select_related(
            "cli",
            "vinc_emp",
            "vinc_fil"
        ).prefetch_related(
            "itens__produto"
        ).get(
            codigo=codigo,
            vinc_emp=request.user.empresa
        )

        if pedido.situacao != "Faturado":
            return JsonResponse({
                "sucesso": False,
                "erro": "Somente pedidos faturados podem ser trocados ou devolvidos."
            })

        itens = []

        for item in pedido.itens.all():
            # 🔥 CORREÇÃO AQUI: Forçamos o Django a calcular a soma filtrando direto pela tabela associativa.
            # Isso ignora completamente a colisão de 'related_name' criada nos models.
            qtd_ja_devolvida = PedidoDevolucaoItem.objects.filter(
                item_pedido=item
            ).aggregate(
                total=Sum("quantidade")
            )["total"] or Decimal("0")

            saldo = item.quantidade - qtd_ja_devolvida

            if saldo <= 0:
                continue

            itens.append({
                "item_id": item.id,
                "produto_id": item.produto.codigo,
                "codigo": item.codigo_usado or item.produto.codigo,
                # Corrigido fallbacks de descrição caso "desc_prod" seja o padrão do seu model
                "descricao": getattr(item.produto, "desc_prod", getattr(item.produto, "descricao", str(item.produto))),
                "valor_unitario": float(item.vl_unit),
                "quantidade_vendida": float(item.quantidade),
                "quantidade_devolvida": float(qtd_ja_devolvida),
                "quantidade_disponivel": float(saldo),
                "subtotal_disponivel": float(saldo * item.vl_unit),
            })

        # 🔥 Se passar por todos os itens e nenhum tiver saldo disponível para devolver
        if not itens:
            return JsonResponse({
                "sucesso": False,
                "erro": f"O pedido nº {codigo} não possui nenhuma quantidade ou saldo disponível para ser devolvido."
            })

        return JsonResponse({
            "sucesso": True,
            "pedido": {
                "id": pedido.id,
                "codigo": pedido.codigo,
                "cliente_id": pedido.cli.codigo,
                "cliente": pedido.nome_cli,
                "total": float(pedido.total),
                "data": timezone.localtime(pedido.dt_fat).strftime("%d/%m/%Y %H:%M") if pedido.dt_fat else "",
            },
            "itens": itens
        })

    except Pedido.DoesNotExist:
        return JsonResponse({
            "sucesso": False,
            "erro": "Pedido não encontrado."
        })

    except Exception as e:
        return JsonResponse({
            "sucesso": False,
            "erro": str(e)
        })

@login_required
@require_POST
def validar_itens_devolucao(request):
    """
    Valida as quantidades a serem devolvidas baseando-se no 'codigo' do pedido da empresa.
    Retorna os dados formatados negativamente para o front-end injetar no carrinho.
    """
    try:
        dados = json.loads(request.body)
        codigo_pedido = dados.get("codigo_pedido")
        itens = dados.get("itens", [])  # Ex: [{"item_id": 12, "quantidade": 2}] (aqui usamos o ID do PedidoProduto para precisão da linha)
        
        if not codigo_pedido or not itens:
            return JsonResponse({"sucesso": False, "erro": "Dados incompletos para validação."})
            
        # Busca o pedido original pelo CÓDIGO da empresa logada
        try:
            pedido_original = Pedido.objects.get(
                codigo=codigo_pedido,
                vinc_emp=request.user.empresa
            )
        except Pedido.DoesNotExist:
            return JsonResponse({"sucesso": False, "erro": "Pedido original não encontrado nesta empresa."})
            
        itens_validados = []
        
        for it in itens:
            item_id = it.get("item_id")  # ID da linha do PedidoProduto
            qtd_devolver = Decimal(str(it.get("quantidade", 0)))
            
            if qtd_devolver <= 0:
                continue
                
            # Garante que o item pertence ao pedido e à empresa correta
            item_pedido = PedidoProduto.objects.select_related('produto').get(
                id=item_id,
                pedido=pedido_original
            )
            
            # Calcula o histórico de devoluções deste item
            qtd_ja_devolvida = PedidoDevolucaoItem.objects.filter(
                item_pedido=item_pedido
            ).aggregate(
                total=Sum("quantidade")
            )["total"] or Decimal("0")
            
            saldo_disponivel = item_pedido.quantidade - qtd_ja_devolvida
            
            if qtd_devolver > saldo_disponivel:
                return JsonResponse({
                    "sucesso": False, 
                    "erro": f"Produto {item_pedido.produto.desc_prod} só possui {saldo_disponivel} unidades disponíveis para devolução."
                })
            
            # Monta a estrutura para o Front-end (com valores negativos)
            itens_validados.append({
                "item_pedido_id": item_pedido.id,  # Mantemos o ID interno oculto para processar o relacionamento depois
                "produto_id": item_pedido.produto.id,
                "codigo_produto": item_pedido.codigo_usado or item_pedido.produto.codigo,
                "descricao": f"<i class='fa-solid fa-arrows-rotate text-primary-emphasis fa-spin me-1' title='Produto a ser devolvido'></i> {item_pedido.produto.desc_prod}",
                "vl_unit": float(item_pedido.vl_unit),
                "quantidade": float(-qtd_devolver),
                "subtotal": float(-(qtd_devolver * item_pedido.vl_unit)),
                "is_devolucao": True
            })
            
        return JsonResponse({"sucesso": True, "itens": itens_validados})
        
    except Exception as e:
        return JsonResponse({"sucesso": False, "erro": str(e)})
    
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

@login_required
def dados_fechamento_caixa(request, caixa_id):
    try:
        caixa = Caixa.objects.get(codigo=caixa_id, vinc_emp=request.user.empresa)

        if caixa.situacao != 'Aberto':
            return JsonResponse({'erro': 'Caixa já está fechado.'}, status=400)

        movs = caixa.movimentos.select_related('forma_pagamento').filter(
            situacao='Ativo'
        )

        totais = defaultdict(lambda: {'forma_id': None, 'descricao': '', 'total': 0.0})

        # Saldo inicial em dinheiro (abertura)
        if caixa.saldo_inicial:
            totais[0]['forma_id'] = 0
            totais[0]['descricao'] = 'SALDO INICIAL'
            totais[0]['total'] += float(caixa.saldo_inicial)

        for m in movs:
            fp = m.forma_pagamento
            if not fp:
                continue
            key = fp.codigo
            totais[key]['forma_id'] = fp.codigo
            totais[key]['descricao'] = fp.descricao.upper()

            if m.tipo == 'Entrada':
                totais[key]['total'] += float(m.valor)
            elif m.tipo == 'Saída':
                totais[key]['total'] -= float(m.valor)

        formas = [v for v in totais.values() if v['descricao']]

        return JsonResponse({'sucesso': True, 'formas': formas})

    except Caixa.DoesNotExist:
        return JsonResponse({'erro': 'Caixa não encontrado.'}, status=404)
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)


@login_required
@require_POST
@transaction.atomic
def fechar_caixa(request, caixa_id):
    try:
        caixa = Caixa.objects.select_for_update().get(
            codigo=caixa_id,
            vinc_emp=request.user.empresa
        )

        if caixa.situacao != 'Aberto':
            return JsonResponse({'erro': 'Caixa já está fechado.'}, status=400)

        data = json.loads(request.body)
        fechamentos = data.get('fechamentos', [])  # [{forma_id, valor_informado}]
        for item in fechamentos:
            forma_codigo = item.get("forma_codigo")

            if not forma_codigo:
                continue

            forma = FormaPgto.objects.get(
                codigo=forma_codigo,
                vinc_emp=request.user.empresa
            )

            CaixaFechamento.objects.create(
                caixa=caixa,
                forma_pagamento=forma,
                valor_registrado=Decimal(str(item["valor_sistema"])),
                valor_informado=Decimal(str(item["valor_informado"])),
                diferenca=Decimal(str(item["valor_informado"])) - Decimal(str(item["valor_sistema"])),
            )

        caixa.situacao = 'Fechado'
        caixa.data_fechamento = timezone.localtime(timezone.now())
        caixa.save(update_fields=['situacao', 'data_fechamento'])

        return JsonResponse({'sucesso': True, 'mensagem': 'Caixa fechado com sucesso!'})

    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)