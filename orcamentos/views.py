from datetime import datetime, timedelta, time
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Orcamento, OrcamentoFormaPgto, PortaOrcamento, PortaProduto, PortaAdicional, SolicitacaoPermissao
from formas_pgto.models import FormaPgto
from .forms import OrcamentoForm, PortaAdicionalForm, PortaProdutoForm, PortaOrcamentoForm
import unicodedata
from django.http import JsonResponse, HttpResponseForbidden
import json
from reportlab.pdfgen import canvas
from io import BytesIO
from django.http import HttpResponse
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
import os
from django.conf import settings
from util.permissoes import verifica_permissao
from PIL import Image
import ast
from clientes.models import Cliente
from tecnicos.models import Tecnico
from django.views.decorators.http import require_POST
from produtos.models import Produto
from notifications.signals import notify
from filiais.models import Filial, Usuario
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from notifications.models import Notification
from decimal import Decimal, InvalidOperation
import locale
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph
from django.forms import inlineformset_factory
from django.db import transaction
from django.template.loader import render_to_string
import base64
from weasyprint import HTML, CSS

PortaFormSet = inlineformset_factory(
    Orcamento, PortaOrcamento,
    form=PortaOrcamentoForm,
    extra=1,
    can_delete=False
)

ProdutoFormSet = inlineformset_factory(
    PortaOrcamento, PortaProduto,
    form=PortaProdutoForm,
    extra=1,
    can_delete=True
)

AdicionalFormSet = inlineformset_factory(
    PortaOrcamento, PortaAdicional,
    form=PortaAdicionalForm,
    extra=1,
    can_delete=True
)


def enviar_solicitacao(request):
    # DEBUG TEMPORÁRIO (pode remover depois)
    # print(request.POST)

    acao = request.POST.get('acao')
    usuario_destino_id = request.POST.get('usuario_id')

    if not usuario_destino_id:
        return JsonResponse(
            {'error': 'ID do usuário destino não enviado.'},
            status=400
        )

    try:
        usuario_destino = Usuario.objects.get(id=usuario_destino_id)
    except Usuario.DoesNotExist:
        return JsonResponse(
            {'error': 'Usuário destino não encontrado.'},
            status=404
        )

    usuario_logado = request.user  # já é Usuario

    # Regra de empresa (obrigatória)
    if usuario_logado.empresa != usuario_destino.empresa:
        return HttpResponseForbidden(
            'Usuário destino não pertence à sua empresa.'
        )

    expiracao = timezone.now() + timedelta(minutes=3)

    solicitacao = SolicitacaoPermissao.objects.create(
        solicitante=usuario_logado,
        autorizado_por=usuario_destino,
        acao=acao,
        expira_em=expiracao
    )

    data_formatada = timezone.localtime(
        solicitacao.expira_em
    ).strftime('%d/%m/%Y %H:%M')

    notify.send(
        usuario_logado,
        recipient=usuario_destino,
        verb=f'Solicitação de permissão ID {solicitacao.id} - {data_formatada}',
        description=f'{usuario_logado.last_name} solicitou permissão para {acao.replace("_", " ")}',
        data={'solicitacao_id': solicitacao.id}
    )

    return JsonResponse({
        'status': 'enviado',
        'id': solicitacao.id,
        'expira_em': solicitacao.expira_em.isoformat()
    })

def verificar_status_solicitacao(request, solicitacao_id):
    try: solicitacao = SolicitacaoPermissao.objects.get(id=solicitacao_id)
    except SolicitacaoPermissao.DoesNotExist: return JsonResponse({'status': 'nao_encontrada'})
    if timezone.now() > solicitacao.expira_em and solicitacao.status == 'Pendente':
        solicitacao.status = 'Expirada'
        solicitacao.save()
    return JsonResponse({'status': solicitacao.status})

@csrf_exempt
def responder_solicitacao(request):
    solicitacao_id = request.POST.get('id')
    acao = request.POST.get('acao')  # 'aprovar' ou 'negar'
    if not solicitacao_id: return JsonResponse({'error': 'ID da solicitação não enviado'}, status=400)
    try: solicitacao = SolicitacaoPermissao.objects.get(id=solicitacao_id)
    except SolicitacaoPermissao.DoesNotExist: return JsonResponse({'error': 'Solicitação não encontrada'}, status=404)
    if acao == 'aprovar': solicitacao.status = 'Aprovada'
    elif acao == 'negar': solicitacao.status = 'Negada'
    else: return JsonResponse({'error': 'Ação inválida'}, status=400)
    solicitacao.save()
    # Marcar notificação como lida
    notifications = Notification.objects.filter(recipient=solicitacao.autorizado_por, verb__icontains=f'ID {solicitacao.id}', unread=True)
    notifications.update(unread=False)
    return JsonResponse({'status': solicitacao.status})

@login_required
def usuarios_com_permissao(request):
    usuario_logado = request.user
    usuarios = Usuario.objects.filter(
        empresa=usuario_logado.empresa,
        gerar_senha_lib=True
    ).order_by('codigo_local')
    lista = [
        {
            'id': u.id,
            'codigo_local': u.codigo_local,
            'username': u.username,
            'nome': u.get_full_name() or u.username
        }
        for u in usuarios
    ]
    return JsonResponse({'usuarios': lista})

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('orcamentos.view_orcamento')
@login_required
def lista_orcamentos(request):
    s = request.GET.get('s')
    f_s = request.GET.get('sit')
    tp_dt = request.GET.get('tp_dt')
    dt_ini = request.GET.get('dt_ini')
    dt_fim = request.GET.get('dt_fim')
    por_dt = request.GET.get('p_dt')
    fil = request.GET.get('fil')
    cli = request.GET.get('cl')
    tec = request.GET.get('tec')
    reg = request.GET.get('reg', '10')
    hoje = datetime.today().date()
    inicio_dia = datetime.combine(hoje, time.min)
    fim_dia = datetime.combine(hoje, time.max)
    ordem = request.GET.get('ordem', 'num_orcamento')
    # BASE — com otimizações
    orcamentos = (Orcamento.objects.filter(vinc_emp=request.user.empresa).select_related('cli', 'vinc_fil', 'solicitante').prefetch_related('formas_pgto__formas_pgto'))
    # Filtro por número
    if s:
        orcamentos = orcamentos.filter(num_orcamento__icontains=s)
    # Filtro por data
    if por_dt == 'Sim' and dt_ini and dt_fim:
        try:
            dt_ini_dt = datetime.combine(datetime.strptime(dt_ini, '%d/%m/%Y').date(), time.min)
            dt_fim_dt = datetime.combine(datetime.strptime(dt_fim, '%d/%m/%Y').date(), time.max)
            if tp_dt == 'Emissão':
                orcamentos = orcamentos.filter(dt_emi__range=(dt_ini_dt, dt_fim_dt))
            elif tp_dt == 'Entrega':
                orcamentos = orcamentos.filter(dt_ent__range=(dt_ini_dt, dt_fim_dt))
            elif tp_dt == 'Fatura':
                orcamentos = orcamentos.filter(dt_fat__range=(dt_ini_dt, dt_fim_dt))
        except ValueError:
            orcamentos = Orcamento.objects.none()
    # Filtro automático do dia
    filtros_ativos = any([s, f_s, por_dt == 'Sim', cli, tec, tp_dt and tp_dt != 'Todos'])
    if not filtros_ativos:
        orcamentos = orcamentos.filter(dt_emi__range=(inicio_dia, fim_dia), situacao='Aberto')
    # Situação
    if f_s and f_s != 'Todos':
        orcamentos = orcamentos.filter(situacao=f_s)
    # Filial
    if fil:
        orcamentos = orcamentos.filter(vinc_fil_id=fil)
    # Cliente
    if cli:
        orcamentos = orcamentos.filter(cli_id=cli)
    # Técnico
    if tec:
        orcamentos = orcamentos.filter(solicitante_id=tec)
    # Ordenação final
    if ordem == '0': orcamentos = orcamentos.order_by('num_orcamento')
    elif ordem == '1': orcamentos = orcamentos.order_by('vinc_fil')
    elif ordem == '2': orcamentos = orcamentos.order_by('cli')
    elif ordem == '3': orcamentos = orcamentos.order_by('solicitante')
    elif ordem == '4': orcamentos = orcamentos.order_by('situacao')
    elif ordem == '5': orcamentos = orcamentos.order_by('dt_emi')
    elif ordem == '6': orcamentos = orcamentos.order_by('dt_ent')
    elif ordem == '7': orcamentos = orcamentos.order_by('dt_fat')
    # Paginação
    if reg == 'todos':
        num_pagina = orcamentos.count() or 1
    else:
        try:
            num_pagina = int(reg) if int(reg) > 0 else 10
        except ValueError:
            num_pagina = 10
    paginator = Paginator(orcamentos, num_pagina)
    page = request.GET.get('page')
    orcamentos = paginator.get_page(page)
    return render(request, 'orcamentos/lista.html', {
        'orcamentos': orcamentos,
        's': s,
        'fil': fil,
        'cli': cli,
        'tec': tec,
        'dt_ini': dt_ini,
        'dt_fim': dt_fim,
        'p_dt': por_dt,
        'tp_dt': tp_dt,
        'reg': reg,
        'ordem': ordem,
        'filiais': Filial.objects.filter(vinc_emp=request.user.empresa),
        'clientes': Cliente.objects.filter(vinc_emp=request.user.empresa),
        'tecnicos': Tecnico.objects.filter(vinc_emp=request.user.empresa),
    })

def paraDecimal(valor):
    try:
        if valor in (None, '', 0):
            return Decimal('0.00')

        # força string
        valor = str(valor).strip()

        # remove separador de milhar
        valor = valor.replace('.', '').replace(',', '.') if ',' in valor else valor

        return Decimal(valor)
    except (InvalidOperation, ValueError):
        return Decimal('0.00')

@login_required
@transaction.atomic
def add_orcamento(request):
    if not request.user.has_perm('orcamentos.add_orcamento'):
        messages.info(request, 'Você não tem permissão para adicionar orçamentos.')
        return redirect('/orcamentos/lista/')
    if request.method == 'POST':
        form = OrcamentoForm(request.POST)
        if not form.is_valid():
            error_messages = [
                f"Campo ({field.label}) é obrigatório!"
                for field in form if field.errors
            ]
            return render(
                request,
                'orcamentos/add_orcamento.html',
                {'form': form, 'error_messages': error_messages}
            )
        # 1. Criar ORÇAMENTO
        dt_emi = form.cleaned_data['dt_emi']
        hora_atual = datetime.now() - timedelta(hours=3)
        data_hora_completa = datetime.combine(dt_emi, hora_atual.time())
        o = form.save(commit=False)
        o.dt_emi = data_hora_completa
        o.situacao = 'Aberto'
        dsct  = paraDecimal(request.POST.get('desconto'))
        acres = paraDecimal(request.POST.get('acrescimo'))
        if request.user.is_authenticated:
            o.vinc_emp = request.user.empresa
        o.save()
        # número do orçamento
        o.num_orcamento = f"{datetime.now():%Y-}{o.id}"
        o.save(update_fields=['num_orcamento'])
        # 2. Portas
        portas_json = request.POST.get("json_portas")
        if portas_json:
            try:
                lista_portas = json.loads(portas_json)
            except json.JSONDecodeError:
                lista_portas = []
            for p in lista_portas:
                porta = PortaOrcamento.objects.create(
                    orcamento=o,
                    numero=p.get("numero", 1),
                    largura=p.get("largura") or 0,
                    altura=p.get("altura") or 0,
                    qtd_lam=p.get("qtd_lam") or 0,
                    m2=p.get("m2") or 0,
                    larg_corte=p.get("larg_corte") or 0,
                    alt_corte=p.get("alt_corte") or 0,
                    rolo=p.get("rolo") or 0,
                    peso=p.get("peso") or 0,
                    fator_peso=p.get("ft_peso") or 0,
                    eixo_motor=p.get("eix_mot") or 0,
                    tp_lamina=p.get("tipo_lamina", "Fechada"),
                    tp_vao=p.get("tipo_vao", "Fora do Vão")
                )
                # 3. Produtos da porta
                for item in p.get("produtos", []):
                    cod = item.get("codProd")
                    qtd = Decimal(item.get("qtdProd", "0"))
                    regra_origem = item.get("regra_origem")
                    if not cod:
                        continue
                    try:
                        produto = Produto.objects.get(pk=cod)
                    except Produto.DoesNotExist:
                        continue
                    pp = PortaProduto.objects.create(
                        porta=porta,
                        produto=produto,
                        quantidade=qtd,
                        regra_origem=regra_origem
                    )
                # 4. Adicionais da porta
                for item in p.get("adicionais", []):
                    cod = item.get("codProd")
                    qtd = Decimal(item.get("qtdProd", "0"))
                    if not cod:
                        continue
                    try:
                        produto = Produto.objects.get(pk=cod)
                    except Produto.DoesNotExist:
                        continue
                    ad = PortaAdicional.objects.create(
                        porta=porta,
                        produto=produto,
                        quantidade=qtd
                    )
        # 5. Formas de Pagamento
        itens_pgto = request.POST.get("json_formas_pgto")

        if itens_pgto:
            try:
                formas = json.loads(itens_pgto)
            except json.JSONDecodeError:
                formas = []

            for f in formas:
                nome = f.get("forma")  # ✅ CORRETO
                valor = Decimal(f.get("valor", "0"))

                if not nome or valor < Decimal("0.01"):
                    continue

                try:
                    fp = FormaPgto.objects.get(descricao=nome)
                except FormaPgto.DoesNotExist:
                    continue

                OrcamentoFormaPgto.objects.create(
                    orcamento=o,
                    formas_pgto=fp,
                    valor=valor
                )

        messages.success(request, "Orçamento criado com sucesso!")
        return redirect('/orcamentos/lista/?s=' + str(o.id))
    else:
        form = OrcamentoForm()
    return render(request, 'orcamentos/add_orcamento.html', {'form': form})


@login_required
@transaction.atomic
def att_orcamento(request, id):
    orcamento = get_object_or_404(
        Orcamento.objects.prefetch_related(
            'portas__produtos__produto',
            'portas__adicionais__produto'
        ),
        pk=id
    )

    if not request.user.has_perm('orcamentos.change_orcamento'):
        messages.info(request, 'Você não tem permissão para editar orçamentos.')
        return redirect('/orcamentos/lista/')

    if orcamento.situacao != 'Aberto':
        messages.warning(request, 'Somente orçamentos em Aberto podem ser editados!')
        return redirect(f'/orcamentos/lista/?s={orcamento.id}')

    form = OrcamentoForm(instance=orcamento)

    if request.method == "POST":
        form = OrcamentoForm(request.POST, instance=orcamento)

        if not form.is_valid():
            erros = [
                f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!"
                for field in form if field.errors
            ]
            return render(request, "orcamentos/att_orcamento.html", {
                "form": form,
                "orcamento": orcamento,
                "error_messages": erros
            })
        # 🔹 Data de emissão
        dt_emi = form.cleaned_data["dt_emi"]
        hora_atual = (datetime.now() - timedelta(hours=3)).time()
        orcamento.dt_emi = datetime.combine(dt_emi, hora_atual)

        # 🔹 Desconto / Acréscimo (seguros)
        dsct = paraDecimal(request.POST.get('desconto'))
        acres = paraDecimal(request.POST.get('acrescimo'))

        orcamento.desconto = dsct
        orcamento.acrescimo = acres

        form.save()

        portas_json = request.POST.get("json_portas")

        try:
            lista_portas = json.loads(portas_json) if portas_json else []
        except json.JSONDecodeError:
            lista_portas = []

        # valida
        lista_portas = [
            p for p in lista_portas
            if isinstance(p, dict) and p.get("largura") and p.get("altura")
        ]

        # 🔥 SÓ AGORA pode deletar
        if lista_portas:
            PortaOrcamento.objects.filter(orcamento=orcamento).delete()

            for p in lista_portas:
                porta = PortaOrcamento.objects.create(
                    orcamento=orcamento,
                    numero=p.get("numero", 1),
                    largura=p.get("largura"),
                    altura=p.get("altura"),
                    qtd_lam=p.get("qtd_lam"),
                    m2=p.get("m2"),
                    larg_corte=p.get("larg_corte"),
                    alt_corte=p.get("alt_corte"),
                    rolo=p.get("rolo"),
                    peso=p.get("peso"),
                    fator_peso=p.get("ft_peso"),
                    eixo_motor=p.get("eix_mot"),
                    tp_lamina=p.get("tipo_lamina", "Fechada"),
                    tp_vao=p.get("tipo_vao", "Fora do Vão"),
                )

                for item in p.get("produtos", []):
                    if not isinstance(item, dict):
                        continue
                    cod = item.get("codProd")
                    qtd = item.get("qtdProd")
                    regra_origem = item.get("regra_origem")
                    if cod:
                        PortaProduto.objects.create(
                            porta=porta,
                            produto_id=cod,
                            quantidade=qtd,
                            regra_origem=regra_origem
                        )

                for item in p.get("adicionais", []):
                    if not isinstance(item, dict):
                        continue
                    cod = item.get("codProd")
                    qtd = item.get("qtdProd")
                    if cod:
                        PortaAdicional.objects.create(
                            porta=porta,
                            produto_id=cod,
                            quantidade=qtd
                        )
        formas_json = request.POST.get("json_formas_pgto")
        if formas_json:
            OrcamentoFormaPgto.objects.filter(orcamento=orcamento).delete()
            formas = json.loads(formas_json)
            for f in formas:
                nome = f.get("forma")
                valor = Decimal(str(f.get("valor", "0")))
                if not nome or valor < Decimal("0.01"):
                    continue
                try:
                    fp = FormaPgto.objects.get(descricao=nome)
                except FormaPgto.DoesNotExist:
                    continue
                OrcamentoFormaPgto.objects.create(
                    orcamento=orcamento,
                    formas_pgto=fp,
                    valor=valor
                )
        # 🔹 Número do orçamento
        orcamento.num_orcamento = f"{datetime.now():%Y-}{orcamento.id}"
        orcamento.save(update_fields=['num_orcamento'])

        messages.success(request, "Orçamento atualizado com sucesso!")
        return redirect(f'/orcamentos/lista/?s={orcamento.id}')
    portas_json = []

    for porta in orcamento.portas.all():
        portas_json.append({
            "numero": porta.numero,
            "largura": float(porta.largura),
            "altura": float(porta.altura),
            "qtd_lam": float(porta.qtd_lam or 0),
            "m2": float(porta.m2 or 0),
            "larg_corte": float(porta.larg_corte or 0),
            "alt_corte": float(porta.alt_corte or 0),
            "rolo": float(porta.rolo or 0),
            "peso": float(porta.peso or 0),
            "ft_peso": float(porta.fator_peso or 0),
            "eix_mot": float(porta.eixo_motor or 0),
            "tipo_lamina": porta.tp_lamina,
            "tipo_vao": porta.tp_vao,

            # 🔥 PRODUTOS NORMAIS
            "produtos": [
                {
                    "codProd": pp.produto.id,
                    "qtdProd": float(pp.quantidade),
                    "regra_origem": pp.regra_origem
                }
                for pp in porta.produtos.all()
            ],

            # 🔥 ADICIONAIS
            "adicionais": [
                {
                    "codProd": adc.produto.id,
                    "qtdProd": float(adc.quantidade)
                }
                for adc in porta.adicionais.all()
            ]
        })
    return render(request, "orcamentos/att_orcamento.html", {
        "form": form,
        "orcamento": orcamento,
        "portas": orcamento.portas.all(),
        "portas_json": json.dumps(portas_json)
    })

@login_required
@transaction.atomic
def clonar_orcamento(request, id):
    orcamento = get_object_or_404(Orcamento, pk=id)

    if not request.user.has_perm('orcamentos.clonar_orcamento'):
        messages.info(request, 'Você não tem permissão para clonar orçamentos.')
        return redirect('/orcamentos/lista/')

    if request.method == 'POST':
        form = OrcamentoForm(request.POST)

        if not form.is_valid():
            erros = [
                f"<i class='fa-solid fa-xmark'></i> Campo ({f.label}) é obrigatório!"
                for f in form if f.errors
            ]
            return render(request, "orcamentos/clonar_orcamento.html", {
                "form": form,
                "orcamento": orcamento,
                "error_messages": erros
            })

        novo = form.save(commit=False)
        novo.situacao = "Aberto"
        novo.vinc_emp = orcamento.vinc_emp
        novo.save()
        novo.num_orcamento = f"{datetime.now():%Y-}{novo.id}"
        novo.save(update_fields=["num_orcamento"])
        # --------- PORTAS ---------
        for porta in orcamento.portas.all():
            nova_porta = PortaOrcamento.objects.create(
                orcamento=novo,
                numero=porta.numero,
                largura=porta.largura,
                altura=porta.altura,
                qtd_lam=porta.qtd_lam,
                m2=porta.m2,
                larg_corte=porta.larg_corte,
                alt_corte=porta.alt_corte,
                rolo=porta.rolo,
                peso=porta.peso,
                fator_peso=porta.fator_peso,
                eixo_motor=porta.eixo_motor,
                tp_lamina=porta.tp_lamina,
                tp_vao=porta.tp_vao,
            )
            for p in porta.produtos.all():
                pp = PortaProduto.objects.create(
                    porta=nova_porta,
                    produto=p.produto,
                    quantidade=p.quantidade
                )
            for ad in porta.adicionais.all():
                pa = PortaAdicional.objects.create(
                    porta=nova_porta,
                    produto=ad.produto,
                    quantidade=ad.quantidade
                )
        # --------- FORMAS PGTO ---------
        for fp in orcamento.formas_pgto.all():
            OrcamentoFormaPgto.objects.create(
                orcamento=novo,
                formas_pgto=fp.formas_pgto,
                valor=fp.valor
            )
        messages.success(request, "Orçamento clonado com sucesso!")
        return redirect('/orcamentos/lista/?s=' + str(novo.id))
    portas_json = []

    for porta in orcamento.portas.all():
        portas_json.append({
            "numero": porta.numero,
            "largura": float(porta.largura),
            "altura": float(porta.altura),
            "qtd_lam": float(porta.qtd_lam or 0),
            "m2": float(porta.m2 or 0),
            "larg_corte": float(porta.larg_corte or 0),
            "alt_corte": float(porta.alt_corte or 0),
            "rolo": float(porta.rolo or 0),
            "peso": float(porta.peso or 0),
            "ft_peso": float(porta.fator_peso or 0),
            "eix_mot": float(porta.eixo_motor or 0),
            "tipo_lamina": porta.tp_lamina,
            "tipo_vao": porta.tp_vao,

            # 🔥 PRODUTOS NORMAIS
            "produtos": [
                {
                    "codProd": pp.produto.id,
                    "qtdProd": float(pp.quantidade)
                }
                for pp in porta.produtos.all()
            ],

            # 🔥 ADICIONAIS
            "adicionais": [
                {
                    "codProd": adc.produto.id,
                    "qtdProd": float(adc.quantidade)
                }
                for adc in porta.adicionais.all()
            ]
        })

    form = OrcamentoForm(instance=orcamento)
    return render(request, "orcamentos/clonar_orcamento.html", {
        "form": form,
        "orcamento": orcamento,
        "portas": orcamento.portas.all(),
        "portas_json": json.dumps(portas_json)
    })

@login_required
def del_orcamento(request, id):
    if not request.user.has_perm('orcamentos.delete_orcamento'):
        messages.info(request, 'Você não tem permissão para deletar orçamentos.')
        return redirect('/orcamentos/lista/')
    o = get_object_or_404(Orcamento, pk=id)
    if o.situacao == 'Faturado' or o.situacao == 'Cancelado':
        messages.warning(request, 'Orçamentos só podem ser deletados com status Aberto!')
        return redirect('/orcamentos/lista/?s=' + str(o.id))
    o.delete()
    messages.success(request, 'Orçamento deletado com sucesso!')
    return redirect('/orcamentos/lista/')

@require_POST
@login_required
@transaction.atomic
def faturar_orcamento(request, id):
    orcamento = get_object_or_404(
        Orcamento.objects.prefetch_related(
            'portas__produtos__produto',
            'portas__adicionais__produto'
        ),
        pk=id
    )
    if not request.user.has_perm('orcamentos.faturar_orcamento'):
        messages.info(request, 'Você não tem permissão para faturar orçamentos!')
        return redirect('/orcamentos/lista/')
    if orcamento.situacao == 'Faturado':
        messages.warning(request, 'Orçamento já está faturado!')
        return redirect('/orcamentos/lista/')
    # 🔥 BAIXA DE ESTOQUE — PRODUTOS E ADICIONAIS (POR PORTA)
    for porta in orcamento.portas.all():
        # Produtos da porta
        for item in porta.produtos.all():
            produto = item.produto
            produto.estoque_prod -= item.quantidade
            produto.save(update_fields=['estoque_prod'])
        # Adicionais da porta
        for item in porta.adicionais.all():
            produto = item.produto
            produto.estoque_prod -= item.quantidade
            produto.save(update_fields=['estoque_prod'])
    # 🔄 Atualiza valores antes de faturar
    orcamento.situacao = 'Faturado'
    orcamento.dt_fat = datetime.now()
    orcamento.save(update_fields=['situacao', 'dt_fat'])
    messages.success(request, f'Orçamento {orcamento.num_orcamento} faturado com sucesso!')
    return redirect('/orcamentos/lista/')

@require_POST
@login_required
@transaction.atomic
def cancelar_orcamento(request, id):
    orcamento = get_object_or_404(
        Orcamento.objects.prefetch_related(
            'portas__produtos__produto',
            'portas__adicionais__produto'
        ),
        pk=id
    )
    if not request.user.has_perm('orcamentos.cancelar_orcamento'):
        messages.info(request, 'Você não tem permissão para cancelar orçamentos!')
        return redirect('/orcamentos/lista/')
    motivo = request.POST.get('motivo', '').strip()
    if not motivo:
        messages.info(request, 'Motivo do cancelamento é obrigatório!')
        return redirect('/orcamentos/lista/')
    if orcamento.situacao == 'Faturado':
        # 🔥 BAIXA DE ESTOQUE — PRODUTOS E ADICIONAIS (POR PORTA)
        for porta in orcamento.portas.all():
            # Produtos da porta
            for item in porta.produtos.all():
                produto = item.produto
                produto.estoque_prod += item.quantidade
                produto.save(update_fields=['estoque_prod'])
            # Adicionais da porta
            for item in porta.adicionais.all():
                produto = item.produto
                produto.estoque_prod += item.quantidade
                produto.save(update_fields=['estoque_prod'])
        # 🔄 Atualiza valores antes de faturar
        orcamento.situacao = 'Cancelado'
        orcamento.dt_fat = datetime.now()
        orcamento.save(update_fields=['situacao', 'dt_fat'])
        messages.success(request, f'Orçamento {orcamento.num_orcamento} cancelado com sucesso!')
        return redirect('/orcamentos/lista/')

@login_required
@require_POST
def alterar_status_orcamento(request):
    try:
        orc_id = request.POST.get("id")
        novo_status = request.POST.get("status")
        if not orc_id or not novo_status:
            return JsonResponse({
                "status": "erro",
                "mensagem": "Dados inválidos"
            }, status=400)
        orc = get_object_or_404(Orcamento, pk=orc_id)
        orc.status = novo_status
        orc.save(update_fields=["status"])
        return JsonResponse({
            "status": "ok",
            "mensagem": "Status atualizado com sucesso!"
        })
    except Exception as e:
        return JsonResponse({
            "status": "erro",
            "mensagem": str(e)
        }, status=500)

@login_required
def imprimir_comprovante(request, id):
    orcamento = get_object_or_404(Orcamento, pk=id)
    # Pegando todas as formas de pagamento relacionadas
    formas_pgto = orcamento.formas_pgto.all()
    # Criando uma lista de formas convertidas para uso no template
    orcamento.formas_convertidas = [
        {
            "id": f.id,
            "descricao": f.formas_pgto.descricao if hasattr(f, 'formas_pgto') else str(f),
            "valor": float(f.valor)
        }
        for f in formas_pgto
    ]
    return render(request, 'orcamentos/comprovante.html', {
        'orcamento': orcamento,
        'formas_pgto': formas_pgto,
    })

segoe_ui_bold = os.path.join(settings.BASE_DIR, "static", "fonts", "segoe-ui-bold.ttf")
segoe_ui = os.path.join(settings.BASE_DIR, "static", "fonts", "Segoe UI.ttf")
arial_narrow_bold = os.path.join(settings.BASE_DIR, "static", "fonts", "arialnarrow_bold.ttf")
times = os.path.join(settings.BASE_DIR, "static", "fonts", "Times.ttf")
times_bold = os.path.join(settings.BASE_DIR, "static", "fonts", "Times_Bold.ttf")
times_bold_italic = os.path.join(settings.BASE_DIR, "static", "fonts", "Times-Bold-Italic.ttf")

@login_required
def imprimir_comp_a4(request, id):
    orcamento = get_object_or_404(Orcamento, pk=id)
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    larg_pag, alt_pag = A4
    pdfmetrics.registerFont(TTFont('Times', times))
    pdfmetrics.registerFont(TTFont('Times Bold', times_bold))
    c.setTitle(f'RESUMO ORÇAMENTO - {orcamento.num_orcamento}')
    c.setFont("Times", 10)

    logo_path = os.path.join(settings.MEDIA_ROOT, str(orcamento.vinc_fil.logo))
    if os.path.exists(logo_path):
        with Image.open(logo_path) as img:
            if img.mode in ('RGBA', 'LA'):
                background = Image.new("RGB", img.size, (255, 255, 255))  # branco
                background.paste(img, mask=img.split()[3])  # usar alpha como máscara
                img = background
            else:
                img = img.convert("RGB")
            c.drawImage(ImageReader(img), (larg_pag - 8*cm)/2, alt_pag-4*cm, width=8*cm, height=3*cm)
    y = alt_pag - 3.5*cm
    filial = request.user.filial_user
    dados_filial = [
        filial.fantasia.upper(),
        filial.cnpj,
        f"{filial.endereco.upper()}, {filial.numero} - {filial.bairro_fil}",
        filial.cidade_fil,
        filial.tel
    ]
    y -= 20
    c.setFont("Times Bold", 12)
    for linha in dados_filial:
        c.drawCentredString(larg_pag/2, y, str(linha))
        y -= 14
    y -= 20
    c.line(40, y, larg_pag-40, y)
    y -= 16
    c.setFont("Times Bold", 14)
    c.drawCentredString(larg_pag/2, y, f"Resumo Orçamento {orcamento.num_orcamento} ({orcamento.situacao})")
    y -= 8
    c.line(40, y, larg_pag-40, y)
    y -= 20
    col_1 = [
        ("Nº Orçamento:", orcamento.num_orcamento), ("Dt. Emissão:", orcamento.dt_emi.strftime("%d/%m/%Y")),
        ("Solicitante:", orcamento.nome_solicitante), ("Razão Social:", orcamento.cli.razao_social),
        ("Cliente:", f"{orcamento.cli.id} - {orcamento.nome_cli}"), ("Endereço:", f"{orcamento.cli.endereco}, Nº {orcamento.cli.numero}"),
        ("CPF/CNPJ:", orcamento.cli.cpf_cnpj),
    ]
    col_2 = [
        ("Bairro:", orcamento.cli.bairro), ("Cidade:", orcamento.cli.cidade), ("UF:", orcamento.cli.uf),
        ("E-mail:", orcamento.cli.email),
    ]
    c.setFont("Times Bold", 9)
    c.drawString(175, y, f"HORA: {orcamento.dt_emi.strftime('%H:%M')}")
    c.drawRightString(larg_pag-40, y, f"IMPRESSO: {request.user.first_name}")
    for label, valor in col_1:
        c.setFont("Times Bold", 9)
        c.drawString(40, y, label)
        c.setFont("Times", 9)
        c.drawString(110, y, str(valor))
        y -= 14
    for label, valor in col_2:
        c.setFont("Times Bold", 9)
        c.drawString(350, y + 56, label)
        c.setFont("Times", 9)
        c.drawString(400, y + 56, str(valor))
        y -= 14
    y += 40
    c.line(40, y, larg_pag-40, y)
    y -= 12
    c.setFont("Times Bold", 10)
    c.drawCentredString(larg_pag/2, y, "RESUMO DAS FORMAS DE PAGAMENTO")
    y -= 6
    c.line(40, y, larg_pag-40, y)
    formas_pgto = orcamento.formas_pgto.all()
    for i, f in enumerate(formas_pgto, 1):
        c.setFont("Times", 9)
        c.drawString(50, y-12, f"{i:03d}")
        c.drawString(100, y-12, f.formas_pgto.descricao)
        c.drawRightString(larg_pag-50, y-12, f"R$ {f.valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        y -= 14
    y -= 20
    totais = [
        ("SUBTOTAL", orcamento.subtotal),
        ("DESCONTO", orcamento.desconto),
        ("ACRÉSCIMO", orcamento.acrescimo),
        ("TOTAL", orcamento.total),
    ]
    c.setFont("Times Bold", 10)
    for label, valor in totais:
        c.drawRightString(larg_pag-50, y, f"{label}: R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        y -= 14
    if orcamento.obs_form_pgto:
        y -= 20
        c.setFont("Times Bold", 10)
        c.drawCentredString(larg_pag/2, y, "OBSERVAÇÕES")
        y -= 14
        style = ParagraphStyle(name="Justify", alignment=TA_JUSTIFY, fontName="Times", fontSize=9)
        Paragraph(orcamento.obs_form_pgto, style).wrapOn(c, larg_pag-100, 100)
        Paragraph(orcamento.obs_form_pgto, style).drawOn(c, 50, y-60)
        y -= 80
    if orcamento.vinc_fil.info_comp:
        y -= 20
        c.setFont("Times", 10)
        c.drawCentredString(larg_pag/2, y, orcamento.vinc_fil.info_comp)
    y -= 80
    c.line(larg_pag - 40, y, larg_pag - 240, y)  # Linha da direita
    c.line(40, y, 240, y)  # Linha da esquerda
    c.setFont("Times Bold", 10)
    c.drawCentredString(larg_pag - 140, y - 15, "Responsável")  # Ajuste o 'y' conforme necessário
    c.drawCentredString(140, y - 15, orcamento.nome_cli)
    c.showPage()
    c.save()
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="RESUMO ORÇAMENTO - {orcamento.num_orcamento}.pdf"'
    return response

from reportlab.lib.utils import simpleSplit
from weasyprint.text.fonts import FontConfiguration
from django.template.loader import render_to_string

@login_required
def pdf_contrato_html(request, id):
    o = Orcamento.objects.prefetch_related(
        'portas__produtos__produto',
        'portas__adicionais__produto'
    ).get(pk=id)

    portas = o.portas.all().order_by('numero')
    formas_pgto = o.formas_pgto.all()
    linhas_formas = max(formas_pgto.count(), 4)

    # =========================
    # LOGO EM BASE64
    # =========================
    logo_base64 = None
    logo_path = os.path.join(settings.MEDIA_ROOT, str(o.vinc_fil.logo))

    if o.vinc_fil.logo and os.path.exists(logo_path):
        with Image.open(logo_path) as img:
            if img.mode in ('RGBA', 'LA'):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            else:
                img = img.convert("RGB")

            buffer = BytesIO()
            img.save(buffer, format="JPEG")
            logo_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    # =========================
    # HTML (CSS EMBUTIDO)
    # =========================
    html_string = render_to_string(
        'orcamentos/pdf_contrato.html',
        {
            'o': o,
            'portas': portas,
            'linhas_formas': linhas_formas,
            'logo_base64': logo_base64,
        }
    )

    # =========================
    # GERAR PDF (SEM CSS EXTERNO)
    # =========================
    pdf = HTML(
        string=html_string,
        base_url=request.build_absolute_uri('/')
    ).write_pdf()

    # =========================
    # RESPONSE
    # =========================
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'inline; filename="CONTRATO ORÇAMENTO PORTA ENROLAR - {o.num_orcamento}.pdf"'
    )

    return response

@login_required
def pdf_contrato_v2(request, id):
    """Gera o PDF da proposta comercial (dinâmico, baseado no orçamento)."""
    o = Orcamento.objects.get(pk=id)
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    larg_pag, alt_pag = A4
    y = alt_pag - 70
    pdfmetrics.registerFont(TTFont('Times', times))
    pdfmetrics.registerFont(TTFont('Times Bold', times_bold))
    pdfmetrics.registerFont(TTFont('Times Bold Italic', times_bold_italic))
    p.setTitle(f"Proposta Comercial - {o.num_orcamento}")
    # --- Logo ---
    logo_path = os.path.join(settings.MEDIA_ROOT, str(o.vinc_fil.logo))
    if os.path.exists(logo_path):
        with Image.open(logo_path) as img:
            if img.mode in ('RGBA', 'LA'):
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            p.drawImage(ImageReader(img), (larg_pag - 6*cm)/100, alt_pag-3*cm, width=6*cm, height=2.25*cm)
    y -= 20
    # --- Funções auxiliares ---
    def write_line(text, font_size=12, gap=14, bold=False):
        nonlocal y
        font = "Times Bold" if bold else "Helvetica"
        p.setFont(font, font_size)
        lines = simpleSplit(text, font, font_size, larg_pag - 50)
        for line in lines:
            p.drawString(30, y, line)
            y -= gap
    # --- Cabeçalho ---
    p.setFont("Times Bold", 16)
    p.drawString(40, y, "Proposta Comercial")
    y -= 20
    p.setFont("Times Bold Italic", 14)
    # Texto centralizado
    texto = "Instalação de Porta de Enrolar Automática"
    p.drawCentredString(larg_pag / 2, y, texto)
    # Linha abaixo do texto
    largura_texto = p.stringWidth(texto, "Helvetica", 12)  # Fonte e tamanho devem ser iguais ao do texto
    x_inicio = (larg_pag - largura_texto) / 2
    x_fim = x_inicio + largura_texto
    p.line(x_inicio - 6, y - 2, x_fim + 6, y - 2)  # linha 2 pontos abaixo do texto
    y -= 40
    p.setFont("Helvetica", 12)
    # --- Corpo ---
    write_line(f"A {o.fantasia_emp}, apresenta a seguinte proposta para fornecimento e instalação de porta de enrolar automática:", bold=False)
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    p.drawString(30, y, "✔ Descrição do Serviço:")
    p.setFont("Helvetica", 12)
    y -= 20
    p.drawString(40, y, "• Fornecimento de porta de enrolar automática sob medida;")
    y -= 15
    p.drawString(40, y, "• Estrutura em aço galvanizado com pintura eletrostática;")
    y -= 15
    p.drawString(40, y, "• Motor automatizador com 2 controles remoto;")
    y -= 15
    p.drawString(40, y, "• Instalação completa e testes de funcionamento.")
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    p.drawString(30, y, "✔ Diferenciais:")
    p.setFont("Helvetica", 12)
    y -= 20
    p.drawString(40, y, "• Profissionais qualificados;")
    y -= 15
    p.drawString(40, y, "• Equipamentos de alta durabilidade;")
    y -= 15
    p.drawString(40, y, "• Garantia de 12 meses;")
    y -= 15
    p.drawString(40, y, "• Suporte técnico LOCAL e especializado.")
    y -= 20
    # --- Valor e condições ---
    p.setFont("Helvetica-Bold", 12)
    p.drawString(30, y, "✔ Especificações das Portas:")
    y -= 20

    for porta in o.portas.all().order_by("numero"):
        # Verifica portinhola APENAS desta porta
        tem_portinhola = porta.adicionais.filter(
            produto__desc_prod__iexact="PORTINHOLA",
            quantidade__gte=1
        ).exists()

        texto_porta = (
            f"• Porta {porta.numero}: "
            f"{porta.altura}m de Altura x {porta.largura}m de Largura"
        )

        if o.pintura == "Sim" and tem_portinhola:
            texto_porta += f", com Pintura de cor {o.cor} e com Portinhola."
        elif o.pintura == "Sim" and not tem_portinhola and o.portao_social == "Não":
            texto_porta += f", com Pintura de cor {o.cor} e sem Portinhola."
        elif o.pintura != "Sim" and tem_portinhola and o.portao_social == "Sim":
            texto_porta += ", sem Pintura e com Portinhola."
        else:
            texto_porta += ", sem Pintura e sem Portinhola."

        write_line(texto_porta, font_size=11)
        y -= 5

        # Controle de quebra de página
        if y < 100:
            p.showPage()
            y = alt_pag - 70
            p.setFont("Helvetica", 11)
    y -= 5
    p.setFont("Helvetica-Bold", 12)
    if o.portao_social == "Sim":
        p.drawString(
            30,
            y,
            f"Observações: Com instalação de Portão Social, valor: R$ {o.vl_p_s}."
        )
    else:
        p.drawString(
            30,
            y,
            "Observações: Sem instalação de Portão Social."
        )
    y -= 20
    # TOTAL GERAL
    p.setFont("Helvetica-Bold", 12)
    vl_tot_fmt = f"{o.total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    p.drawString(
        30,
        y,
        f"✔ Valor total do fornecimento e instalação: R$ {vl_tot_fmt}."
    )
    y -= 20
    p.setFont("Helvetica", 12)
    dez_p = o.total * Decimal('0.10')
    vl_dsct = o.total - dez_p
    vl_dsct_fmt = f"{vl_dsct:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    p.drawString(
        30,
        y,
        f"Valor acima em até 10x nos cartões de crédito ou À VISTA com 10% de desconto! (R$ {vl_dsct_fmt})"
    )

    y -= 25

    p.setFont("Helvetica-Bold", 12)
    texto_bold = "✔ Forma de Pagamento:"
    p.drawString(30, y, texto_bold)
    largura_titulo = p.stringWidth(texto_bold, "Helvetica-Bold", 12)
    p.setFont("Helvetica", 12)
    p.drawString(30 + largura_titulo + 5, y, "50% no ato do fechamento e valor restante ao finalizar a instalação.")
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    texto_bold = "✔ Prazo de Instalação:"
    p.drawString(30, y, texto_bold)
    largura_titulo = p.stringWidth(texto_bold, "Helvetica-Bold", 12)
    p.setFont("Helvetica", 12)
    p.drawString(30 + largura_titulo + 5, y, "Até 20 dias úteis após a aprovação e pagamento, podendo variar de acordo")
    y -= 15
    p.drawString(30, y, "com estrutura do local de instalação.")
    y -= 25
    p.drawString(30, y, "Qualquer dúvida ou necessidade de ajuste, estamos à disposição!")
    y -= 40
    # --- Rodapé ---
    p.setFont("Helvetica-Bold", 12)
    p.drawString(30, y, f"{o.vinc_fil.info_comp}")
    y -= 30
    ic_tel = os.path.join(settings.BASE_DIR, "static", "img", "telefone.png")
    ic_email = os.path.join(settings.BASE_DIR, "static", "img", "email.png")
    ic_loc = os.path.join(settings.BASE_DIR, "static", "img", "local.png")
    p.drawImage(ic_tel, 30, y, width=15, height=15)
    p.drawString(50, y + 4, f"{o.vinc_fil.tel}")
    y -= 20
    p.drawImage(ic_email, 30, y, width=15, height=15)
    p.drawString(50, y + 4, f"{o.vinc_fil.email}")
    y -= 20
    p.drawImage(ic_loc, 30, y, width=15, height=15)
    p.drawString(50, y + 4, "Atendemos em todo estado do Pará!")
    y -= 20
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    data_formatada = o.dt_emi.strftime('%d de %B de %Y').upper()
    p.drawString(30, y, f"{o.vinc_fil.cidade_fil} - {o.vinc_fil.uf}, {data_formatada}.")
    y -= 100
    p.line(100, y, larg_pag - 100, y)
    y -= 15
    p.drawCentredString(larg_pag / 2, y, f"{o.cli}")
    p.showPage()
    p.save()
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')

@login_required
def pdf_orcamento_html(request, id):
    o = Orcamento.objects.prefetch_related(
        'portas__produtos__produto',
        'portas__adicionais__produto'
    ).get(pk=id)
    portas = o.portas.all().order_by('numero')
    formas_pgto = o.formas_pgto.all()
    linhas_formas = max(formas_pgto.count(), 4)
    logo_base64 = None
    if o.vinc_fil.logo:
        logo_path = os.path.join(settings.MEDIA_ROOT, str(o.vinc_fil.logo))
        if os.path.exists(logo_path):
            with Image.open(logo_path) as img:
                if img.mode in ('RGBA', 'LA'):
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[-1])
                    img = bg
                else:
                    img = img.convert("RGB")
                buffer = BytesIO()
                img.save(buffer, format="JPEG")
                logo_base64 = base64.b64encode(buffer.getvalue()).decode()
    html = render_to_string('orcamentos/pdf_orcamento.html',
        {
            'o': o,
            'portas': portas,
            'linhas_formas': linhas_formas,
            'logo_base64': logo_base64,
        },
        request=request
    )
    pdf = HTML(string=html, base_url=request.build_absolute_uri('/') ).write_pdf(
        stylesheets=[
            CSS(string="""
                @page {
                    size: A4;
                    margin: 25mm 15mm 20mm 15mm;
                }
                body {
                    font-family: Arial, sans-serif;
                    font-size: 11px;
                }
            """)
        ]
    )
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="ORÇAMENTO PORTA ENROLAR - {o.num_orcamento}.pdf"'
    )
    return response
