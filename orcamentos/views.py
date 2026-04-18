from datetime import datetime, timedelta, time, date
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
from clientes.models import Cliente
from tecnicos.models import Tecnico
from contas_receber.models import ContaReceber
from django.views.decorators.http import require_POST
from produtos.models import Produto
from notifications.signals import notify
from filiais.models import Filial, Usuario
from django.views.decorators.csrf import csrf_exempt
from notifications.models import Notification
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import locale
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import cm
from django.contrib.auth.hashers import check_password
from django.forms import inlineformset_factory
from django.db import transaction
from django.template.loader import render_to_string
import base64
from weasyprint import HTML, CSS
from django.contrib.staticfiles import finders
from django.db.models import Prefetch
from django.db import DatabaseError, IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Exists, OuterRef

PortaFormSet = inlineformset_factory( Orcamento, PortaOrcamento, form=PortaOrcamentoForm, extra=1, can_delete=False )
ProdutoFormSet = inlineformset_factory( PortaOrcamento, PortaProduto, form=PortaProdutoForm, extra=1, can_delete=True )
AdicionalFormSet = inlineformset_factory( PortaOrcamento, PortaAdicional, form=PortaAdicionalForm, extra=1, can_delete=True )

@login_required
@require_POST
def enviar_solicitacao(request):
    acao = request.POST.get('acao')
    usuario_destino_id = request.POST.get('usuario_id')
    modulo = request.POST.get('modulo')
    registro_desc = request.POST.get('registro_desc')
    if not usuario_destino_id:
        return JsonResponse({'error': 'ID do usuário destino não enviado.'}, status=400)
    usuario_logado = request.user
    empresa = usuario_logado.empresa
    try:
        usuario_destino = Usuario.objects.get(id=usuario_destino_id, empresa=empresa)
    except Usuario.DoesNotExist:
        return JsonResponse({'error': 'Usuário destino não encontrado.'}, status=404)
    expiracao = timezone.now() + timedelta(minutes=3)
    solicitacao = SolicitacaoPermissao.objects.create(vinc_emp=empresa, solicitante=usuario_logado, autorizado_por=usuario_destino, acao=acao, expira_em=expiracao)
    data_formatada = timezone.localtime(solicitacao.expira_em).strftime('%d/%m/%Y %H:%M')
    descricao = (
        f"{usuario_logado.first_name} solicitou liberação para "
        f"{acao.replace('_', ' ')} no módulo {modulo}. "
        f"Registro: {registro_desc}"
    )
    notify.send(usuario_logado, recipient=usuario_destino, verb=f"Solicitação de Permissão ID {solicitacao.id} - {data_formatada}", description=descricao, data={'solicitacao_id': solicitacao.id})
    return JsonResponse({'status': 'enviado', 'id': solicitacao.id, 'expira_em': solicitacao.expira_em.isoformat()})

@login_required
def verificar_status_solicitacao(request, solicitacao_id):
    try:
        solicitacao = SolicitacaoPermissao.objects.get(id=solicitacao_id, vinc_emp=request.user.empresa)
    except SolicitacaoPermissao.DoesNotExist:
        return JsonResponse({'status': 'nao_encontrada'})
    if timezone.now() > solicitacao.expira_em and solicitacao.status == 'Pendente':
        solicitacao.status = 'Expirada'
        solicitacao.save(update_fields=['status'])
    return JsonResponse({'status': solicitacao.status})

@login_required
@require_POST
def responder_solicitacao(request):
    solicitacao_id = request.POST.get('id')
    acao = request.POST.get('acao')
    if not solicitacao_id:
        return JsonResponse({'error': 'ID da solicitação não enviado'}, status=400)
    try:
        solicitacao = SolicitacaoPermissao.objects.get(id=solicitacao_id, vinc_emp=request.user.empresa, autorizado_por=request.user)
    except SolicitacaoPermissao.DoesNotExist:
        return JsonResponse({'error': 'Solicitação não encontrada'}, status=404)
    if timezone.now() > solicitacao.expira_em and solicitacao.status == 'Pendente':
        solicitacao.status = 'Expirada'
        solicitacao.save(update_fields=['status'])
        Notification.objects.filter(recipient=solicitacao.autorizado_por, verb__icontains=f'ID {solicitacao.id}', unread=True).update(unread=False)
        return JsonResponse({'status': 'Expirada'})
    if acao == 'aprovar':
        solicitacao.status = 'Aprovada'
    elif acao == 'negar':
        solicitacao.status = 'Negada'
    else:
        return JsonResponse({'error': 'Ação inválida'}, status=400)
    solicitacao.save(update_fields=['status'])
    Notification.objects.filter(recipient=solicitacao.autorizado_por, verb__icontains=f'ID {solicitacao.id}', unread=True).update(unread=False)
    return JsonResponse({'status': solicitacao.status})

@login_required
def usuarios_com_permissao(request):
    usuario_logado = request.user
    usuarios = Usuario.objects.filter(empresa=usuario_logado.empresa, gerar_senha_lib=True).order_by('codigo_local')
    lista = [{'id': u.id, 'codigo_local': u.codigo_local, 'username': u.username, 'nome': u.get_full_name() or u.username} for u in usuarios]
    return JsonResponse({'usuarios': lista})

@login_required
@require_POST
def liberar_com_senha(request):
    usuario_id = request.POST.get('usuario_id')
    senha = request.POST.get('senha')
    if not usuario_id or not senha:
        return JsonResponse({'status': 'erro'}, status=400)
    try:
        autorizador = Usuario.objects.get(id=usuario_id, empresa=request.user.empresa, gerar_senha_lib=True)
    except Usuario.DoesNotExist:
        return JsonResponse({'status': 'erro'}, status=404)
    if not check_password(senha, autorizador.password):
        return JsonResponse({'status': 'senha_incorreta'})
    return JsonResponse({'status': 'Aprovada'})

@login_required
@require_POST
def expirar_solicitacao(request):
    try:
        solicitacao = SolicitacaoPermissao.objects.get(id=request.POST.get('id'), vinc_emp=request.user.empresa)
    except SolicitacaoPermissao.DoesNotExist:
        return JsonResponse({'status': 'nao_encontrada'})
    if solicitacao.status == 'Pendente':
        solicitacao.status = 'Expirada'
        solicitacao.save(update_fields=['status'])
        Notification.objects.filter(recipient=solicitacao.autorizado_por, verb__icontains=f'ID {solicitacao.id}', unread=True).update(unread=False)
    return JsonResponse({'status': 'expirada'})

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
    ordem = request.GET.get('ordem', '0')
    hoje = datetime.today().date()
    inicio_dia = datetime.combine(hoje, time.min)
    fim_dia = datetime.combine(hoje, time.max)
    formas_com_parcela = OrcamentoFormaPgto.objects.filter(orcamento=OuterRef('pk'), formas_pgto__gera_parcelas=True)
    orcamentos = (Orcamento.objects.filter(vinc_emp=request.user.empresa).select_related('cli', 'vinc_fil', 'solicitante').prefetch_related('formas_pgto__formas_pgto')).annotate(tem_forma_com_parcela=Exists(formas_com_parcela))
    if s: orcamentos = orcamentos.filter(num_orcamento__icontains=s)
    if por_dt == 'Sim' and dt_ini and dt_fim:
        try:
            dt_ini_dt = datetime.combine(datetime.strptime(dt_ini, '%d/%m/%Y').date(), time.min)
            dt_fim_dt = datetime.combine(datetime.strptime(dt_fim, '%d/%m/%Y').date(), time.max)
            if tp_dt == 'Emissão': orcamentos = orcamentos.filter(dt_emi__range=(dt_ini_dt, dt_fim_dt))
            elif tp_dt == 'Entrega': orcamentos = orcamentos.filter(dt_ent__range=(dt_ini_dt, dt_fim_dt))
            elif tp_dt == 'Fatura': orcamentos = orcamentos.filter(dt_fat__range=(dt_ini_dt, dt_fim_dt))
        except ValueError: orcamentos = Orcamento.objects.none()
    filtros_ativos = any([s, f_s, por_dt == 'Sim', cli, tec, tp_dt and tp_dt != 'Todos'])
    if not filtros_ativos: orcamentos = orcamentos.filter(dt_emi__range=(inicio_dia, fim_dia), situacao='Aberto')
    if f_s and f_s != 'Todos': orcamentos = orcamentos.filter(situacao=f_s)
    if fil: orcamentos = orcamentos.filter(vinc_fil_id=fil)
    if cli: orcamentos = orcamentos.filter(cli_id=cli)
    if tec: orcamentos = orcamentos.filter(solicitante_id=tec)
    if ordem == '0': orcamentos = orcamentos.order_by('num_orcamento')
    elif ordem == '1': orcamentos = orcamentos.order_by('vinc_fil')
    elif ordem == '2': orcamentos = orcamentos.order_by('cli')
    elif ordem == '3': orcamentos = orcamentos.order_by('solicitante')
    elif ordem == '4': orcamentos = orcamentos.order_by('situacao')
    elif ordem == '5': orcamentos = orcamentos.order_by('dt_emi')
    elif ordem == '6': orcamentos = orcamentos.order_by('dt_ent')
    elif ordem == '7': orcamentos = orcamentos.order_by('dt_fat')
    if reg == 'todos': num_pagina = orcamentos.count() or 1
    else:
        try: num_pagina = int(reg) if int(reg) > 0 else 10
        except ValueError: num_pagina = 10
    paginator = Paginator(orcamentos, num_pagina)
    page = request.GET.get('page')
    orcamentos = paginator.get_page(page)
    return render(request, 'orcamentos/lista.html', {
    'orcamentos': orcamentos, 's': s, 'sit': f_s, 'fil': fil, 'cli': cli, 'tec': tec, 'dt_ini': dt_ini, 'dt_fim': dt_fim, 'p_dt': por_dt, 'tp_dt': tp_dt, 'reg': reg, 'ordem': ordem,
    'filiais': Filial.objects.filter(vinc_emp=request.user.empresa),
    'clientes': Cliente.objects.filter(vinc_emp=request.user.empresa),
    'tecnicos': Tecnico.objects.filter(vinc_emp=request.user.empresa),
})

@login_required
def detalhes_orc_ajax(request, id):
    try:
        o = get_object_or_404(
            Orcamento.objects.prefetch_related(
                'portas__produtos__produto__unidProd',
                'portas__adicionais__produto__unidProd'
            ),
            pk=id,
            vinc_emp=request.user.empresa
        )
        portas_data = []
        for porta in o.portas.all().order_by('numero'):
            produtos = []
            adicionais = []
            contador_prod = 1
            for p in porta.produtos.all():
                produtos.append({"item": f"{contador_prod:03}", "codigo": p.produto.id, "produto": p.produto.desc_prod, "unidade": getattr(p.produto.unidProd, "nome_unidade", ""), "valor_unit": str(p.valor_unitario), "qtd": str(p.quantidade), "valor_total": str(p.valor_total), "regra_origem": p.regra_origem or ""})
                contador_prod += 1
            contador_adc = 1
            for a in porta.adicionais.all():
                adicionais.append({"item": f"{contador_adc:03}", "codigo": a.produto.id, "produto": a.produto.desc_prod, "unidade": getattr(a.produto.unidProd, "nome_unidade", ""), "valor_unit": str(a.valor_unitario), "qtd": str(a.quantidade), "valor_total": str(a.valor_total), "regra_origem": a.regra_origem or "", "lado": a.lado or ""})
                contador_adc += 1
            portas_data.append({"numero": porta.numero, "largura": str(porta.largura), "altura": str(porta.altura), "m2": str(porta.m2), "produtos": produtos, "adicionais": adicionais})
        data = {"id": o.id, "num_orcamento": o.num_orcamento, "serial": o.id, "situacao": o.situacao, "status": o.status, "data_emissao": (o.dt_emi - timedelta(hours=3)).strftime("%d/%m/%Y - %H:%M") if o.dt_emi else "", "data_entrega": o.dt_ent.strftime("%d/%m/%Y") if o.dt_ent else "", "cliente": {"nome": o.nome_cli, "empresa": {"nome": o.fantasia_emp}, "tel": getattr(o.cli, "tel", "")}, "colaborador": o.nome_solicitante, "vl_tot": str(o.total), "obs": o.obs_cli, "portas": portas_data}
        return JsonResponse(data)
    except Orcamento.DoesNotExist:
        return JsonResponse({'error': 'Orçamento não encontrado'}, status=404)

def paraDecimal(valor):
    try:
        if valor in (None, '', 0): return Decimal('0.00')
        valor = str(valor).strip()
        valor = valor.replace('.', '').replace(',', '.') if ',' in valor else valor
        return Decimal(valor)
    except (InvalidOperation, ValueError): return Decimal('0.00')

@login_required
@transaction.atomic
def add_orcamento(request):
    error_messages = []
    if not request.user.has_perm('orcamentos.add_orcamento'):
        messages.info(request, 'Você não tem permissão para adicionar orçamentos.')
        return redirect('/orcamentos/lista/')
    try:
        if request.method == 'POST':
            form = OrcamentoForm(request.POST, empresa=request.user.empresa, user=request.user)
            if not form.is_valid():
                error_messages = [f"Campo ({field.label}) é obrigatório!" for field in form if field.errors]
                return render(request, 'orcamentos/add_orcamento.html', {'form': form, 'error_messages': error_messages})
            o = form.save(commit=False)
            if o.cli.vinc_emp != request.user.empresa: return HttpResponseForbidden()
            if o.vinc_fil.vinc_emp != request.user.empresa: return HttpResponseForbidden()
            o.dt_emi = datetime.now()
            o.situacao = 'Aberto'
            o.vinc_emp = request.user.empresa
            o.save()
            o.num_orcamento = f"{datetime.now():%Y-}{o.id}"
            o.save(update_fields=['num_orcamento'])
            portas_json = request.POST.get("json_portas")
            if portas_json:
                try: lista_portas = json.loads(portas_json)
                except json.JSONDecodeError: lista_portas = []
                for p in lista_portas:
                    porta = PortaOrcamento.objects.create(orcamento=o, numero=p.get("numero", 1), largura=p.get("largura") or 0, altura=p.get("altura") or 0, qtd_lam=p.get("qtd_lam") or 0, m2=p.get("m2") or 0, larg_corte=p.get("larg_corte") or 0, alt_corte=p.get("alt_corte") or 0, rolo=p.get("rolo") or 0, peso=p.get("peso") or 0, fator_peso=p.get("ft_peso") or 0, eixo_motor=p.get("eix_mot") or 0, tp_lamina=p.get("tipo_lamina", "Fechada"), tp_vao=p.get("tipo_vao", "Fora do Vão"), op_guia_e=p.get("op_guia_e", "Dentro do Vão"), op_guia_d=p.get("op_guia_d", "Dentro do Vão"),)
                    for item in p.get("produtos", []):
                        cod = item.get("codProd")
                        qtd = Decimal(item.get("qtdProd", "0"))
                        regra_origem = item.get("regra_origem")
                        if not cod: continue
                        try: produto = Produto.objects.get(pk=cod, vinc_emp=request.user.empresa)
                        except Produto.DoesNotExist: continue
                        valor_unitario = Decimal(str(item.get("vl_unit") or "0"))
                        valor_total = Decimal(str(item.get("vl_total") or "0"))
                        if valor_total == 0 and valor_unitario > 0 and qtd: valor_total = valor_unitario * Decimal(str(qtd))
                        PortaProduto.objects.create(porta=porta, produto=produto, quantidade=qtd, valor_unitario=valor_unitario, valor_total=valor_total, regra_origem=regra_origem)
                    for item in p.get("adicionais", []):
                        cod = item.get("codProd")
                        qtd = Decimal(item.get("qtdProd", "0"))
                        regra_origem = item.get("regra_origem")
                        lado = (item.get("lado") or '').strip()
                        if not cod: continue
                        try: produto = Produto.objects.get(pk=cod, vinc_emp=request.user.empresa)
                        except Produto.DoesNotExist: continue
                        valor_unitario = Decimal(str(item.get("vl_unit") or "0"))
                        valor_total = Decimal(str(item.get("vl_total") or "0"))
                        if valor_total == 0 and valor_unitario > 0 and qtd: valor_total = valor_unitario * Decimal(str(qtd))
                        PortaAdicional.objects.create(porta=porta, produto=produto, quantidade=qtd, valor_unitario=valor_unitario, valor_total=valor_total, regra_origem=regra_origem, lado=lado)
            o.atualizar_subtotal()
            if o.subtotal == 0:
                raise ValueError("O orçamento precisa ter pelo menos um item com valor.")
            o.save(update_fields=['subtotal', 'total'])
            itens_pgto = request.POST.get("json_formas_pgto")
            if itens_pgto:
                try: formas = json.loads(itens_pgto)
                except json.JSONDecodeError: formas = []
                for f in formas:
                    nome = f.get("forma")
                    valor = Decimal(str(f.get("valor", "0")))
                    parcelas = int(f.get("parcelas") or 1)
                    dias = int(f.get("dias") or 0)
                    if not nome or valor < Decimal("0.01"): continue
                    try: fp = FormaPgto.objects.get(descricao=nome, vinc_emp=request.user.empresa)
                    except FormaPgto.DoesNotExist: continue
                    OrcamentoFormaPgto.objects.create(orcamento=o, formas_pgto=fp, valor=valor, parcelas=parcelas, dias_intervalo=dias)
            messages.success(request, "Orçamento criado com sucesso!")
            return redirect('/orcamentos/lista/?s=' + str(o.id))
        else: form = OrcamentoForm(empresa=request.user.empresa, user=request.user)
    except ObjectDoesNotExist: error_messages.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {str(e)}")
    except DatabaseError as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco de dados: {str(e)}")
    except Exception as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return render(request, 'orcamentos/add_orcamento.html', {'form': form, 'error_messages': error_messages})

@login_required
@transaction.atomic
def att_orcamento(request, id):
    error_messages = []
    orcamento = get_object_or_404(Orcamento.objects.prefetch_related('portas__produtos__produto', 'portas__adicionais__produto'), pk=id, vinc_emp=request.user.empresa)
    if not request.user.has_perm('orcamentos.change_orcamento'):
        messages.info(request, 'Você não tem permissão para editar orçamentos.')
        return redirect('/orcamentos/lista/')
    if orcamento.situacao != 'Aberto':
        messages.warning(request, 'Somente orçamentos em Aberto podem ser editados!')
        return redirect(f'/orcamentos/lista/?s={orcamento.id}')
    form = OrcamentoForm(instance=orcamento, empresa=request.user.empresa, user=request.user)
    try:
        if request.method == "POST":
            dt_emi_original = orcamento.dt_emi
            form = OrcamentoForm(request.POST, instance=orcamento, empresa=request.user.empresa, user=request.user)
            if not form.is_valid():
                erros = [
                    f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!"
                    for field in form if field.errors
                ]
                return render(request, "orcamentos/att_orcamento.html", {"form": form, "orcamento": orcamento, "error_messages": erros})
            orcamento_editado = form.save(commit=False)
            orcamento_editado.dt_emi = dt_emi_original
            orcamento_editado.desconto = Decimal(str(request.POST.get("desconto") or "0"))
            orcamento_editado.acrescimo = Decimal(str(request.POST.get("acrescimo") or "0"))
            orcamento_editado.save()
            next_url = request.POST.get('next') or request.GET.get('next')
            portas_json = request.POST.get("json_portas")
            try: lista_portas = json.loads(portas_json) if portas_json else []
            except json.JSONDecodeError: lista_portas = []
            lista_portas = [
                p for p in lista_portas
                if isinstance(p, dict) and p.get("largura") and p.get("altura")
            ]
            # guarda lados antigos antes de apagar tudo
            lados_antigos = {}
            for porta_antiga in orcamento.portas.all():
                for adc in porta_antiga.adicionais.all():
                    chave = (int(porta_antiga.numero or 0), int(adc.produto_id or 0), str(adc.regra_origem or '').strip())
                    lados_antigos[chave] = (adc.lado or '').strip()
            PortaOrcamento.objects.filter(orcamento=orcamento).delete()
            for p in lista_portas:
                porta = PortaOrcamento.objects.create(
                    orcamento=orcamento, numero=p.get("numero", 1), largura=p.get("largura"), altura=p.get("altura"), qtd_lam=p.get("qtd_lam"), m2=p.get("m2"), larg_corte=p.get("larg_corte"), alt_corte=p.get("alt_corte"),
                    rolo=p.get("rolo"), peso=p.get("peso"), fator_peso=p.get("ft_peso"), eixo_motor=p.get("eix_mot"), tp_lamina=p.get("tipo_lamina", "Fechada"), tp_vao=p.get("tipo_vao", "Fora do Vão"), op_guia_e=p.get("op_guia_e"), op_guia_d=p.get("op_guia_d"),
                )
                for item in p.get("produtos", []):
                    if not isinstance(item, dict):
                        continue
                    cod = item.get("codProd")
                    qtd = item.get("qtdProd")
                    regra_origem = item.get("regra_origem")
                    if not cod: continue
                    valor_unitario = Decimal(str(item.get("vl_unit") or "0"))
                    valor_total = Decimal(str(item.get("vl_total") or "0"))
                    if valor_total == 0 and valor_unitario > 0 and qtd: valor_total = valor_unitario * Decimal(str(qtd))
                    PortaProduto.objects.create(porta=porta, produto_id=cod, quantidade=qtd, valor_unitario=valor_unitario, valor_total=valor_total, regra_origem=regra_origem)
                for item in p.get("adicionais", []):
                    if not isinstance(item, dict): continue
                    cod = item.get("codProd")
                    qtd = item.get("qtdProd")
                    regra_origem = item.get("regra_origem")
                    lado = (item.get("lado") or '').strip()
                    if not cod: continue
                    # se o lado vier vazio no JSON, tenta reaproveitar o que já existia
                    if not lado:
                        chave = (int(p.get("numero", 1) or 0), int(cod or 0), str(regra_origem or '').strip())
                        lado = lados_antigos.get(chave, '')
                    valor_unitario = Decimal(str(item.get("vl_unit") or "0"))
                    valor_total = Decimal(str(item.get("vl_total") or "0"))
                    if valor_total == 0 and valor_unitario > 0 and qtd: valor_total = valor_unitario * Decimal(str(qtd))
                    PortaAdicional.objects.create(porta=porta, produto_id=cod, quantidade=qtd, valor_unitario=valor_unitario, valor_total=valor_total, regra_origem=regra_origem, lado=lado)
            formas_json = request.POST.get("json_formas_pgto")
            if formas_json:
                OrcamentoFormaPgto.objects.filter(orcamento=orcamento).delete()
                try: formas = json.loads(formas_json)
                except: formas = []
                for f in formas:
                    nome = f.get("forma")
                    valor = Decimal(str(f.get("valor") or "0"))
                    parcelas = int(f.get("parcelas") or 1)
                    dias = int(f.get("dias") or 0)
                    if not nome or valor <= 0: continue
                    try: fp = FormaPgto.objects.get(descricao=nome, vinc_emp=request.user.empresa)
                    except FormaPgto.DoesNotExist: continue
                    OrcamentoFormaPgto.objects.create(orcamento=orcamento, formas_pgto=fp, valor=valor, parcelas=parcelas, dias_intervalo=dias)
            orcamento.num_orcamento = f"{datetime.now():%Y-}{orcamento.id}"
            orcamento.save(update_fields=["num_orcamento"])
            messages.success(request, "Orçamento atualizado com sucesso!")
            if next_url:
                return redirect(next_url)
            else:
                return redirect(f'/orcamentos/lista/?s={orcamento.id}')
    except ObjectDoesNotExist: error_messages.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {str(e)}")
    except DatabaseError as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except Exception as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    portas_json = []
    for porta in orcamento.portas.all():
        portas_json.append({"numero": porta.numero, "largura": float(porta.largura), "altura": float(porta.altura), "qtd_lam": float(porta.qtd_lam or 0), "m2": float(porta.m2 or 0), "larg_corte": float(porta.larg_corte or 0),
            "alt_corte": float(porta.alt_corte or 0), "rolo": float(porta.rolo or 0), "peso": float(porta.peso or 0), "ft_peso": float(porta.fator_peso or 0), "eix_mot": float(porta.eixo_motor or 0),
            "tipo_lamina": porta.tp_lamina, "tipo_vao": porta.tp_vao, "op_guia_e": porta.op_guia_e, "op_guia_d": porta.op_guia_d,
            "produtos":[{"codProd":pp.produto.id,"qtdProd":float(pp.quantidade),"regra_origem":pp.regra_origem,"vl_unit":float(pp.valor_unitario or 0),"vl_total":float(pp.valor_total or 0)} for pp in porta.produtos.all()],
            "adicionais":[{"codProd":adc.produto.id,"qtdProd":float(adc.quantidade),"lado":adc.lado,"regra_origem":adc.regra_origem,"vl_unit":float(adc.valor_unitario or 0),"vl_total":float(adc.valor_total or 0)} for adc in porta.adicionais.all()]
        })
    return render(request, "orcamentos/att_orcamento.html",{"form": form, "orcamento": orcamento, "error_messages": error_messages, "portas": orcamento.portas.all(), "portas_json": json.dumps(portas_json)})

@login_required
@transaction.atomic
def clonar_orcamento(request, id):
    error_messages = []
    orcamento = get_object_or_404(Orcamento, pk=id, vinc_emp=request.user.empresa)
    if not request.user.has_perm('orcamentos.clonar_orcamento'):
        messages.info(request, 'Você não tem permissão para clonar orçamentos.')
        return redirect('/orcamentos/lista/')
    try:
        if request.method == 'POST':
            form = OrcamentoForm(request.POST, empresa=request.user.empresa, user=request.user)
            if not form.is_valid():
                erros = [
                    f"<i class='fa-solid fa-xmark'></i> Campo ({f.label}) é obrigatório!"
                    for f in form if f.errors
                ]
                return render(request, "orcamentos/clonar_orcamento.html", {"form": form, "orcamento": orcamento, "error_messages": erros})
            novo = form.save(commit=False)
            dt_emi = form.cleaned_data['dt_emi']
            hora_atual = datetime.now() - timedelta(hours=3)
            data_hora_completa = datetime.combine(dt_emi, hora_atual.time())
            novo.dt_emi = data_hora_completa
            novo.situacao = "Aberto"
            novo.vinc_emp = orcamento.vinc_emp
            novo.save()
            novo.num_orcamento = f"{datetime.now():%Y-}{novo.id}"
            novo.save(update_fields=["num_orcamento"])
            next_url = request.POST.get('next') or request.GET.get('next')
            for porta in orcamento.portas.all():
                nova_porta = PortaOrcamento.objects.create(orcamento=novo, numero=porta.numero, largura=porta.largura, altura=porta.altura, qtd_lam=porta.qtd_lam, m2=porta.m2,
                    larg_corte=porta.larg_corte, alt_corte=porta.alt_corte, rolo=porta.rolo, peso=porta.peso, fator_peso=porta.fator_peso, eixo_motor=porta.eixo_motor,
                    tp_lamina=porta.tp_lamina, tp_vao=porta.tp_vao, op_guia_e=porta.op_guia_e, op_guia_d=porta.op_guia_d)
                for p in porta.produtos.all():
                    PortaProduto.objects.create(porta=nova_porta, produto=p.produto, quantidade=p.quantidade, valor_unitario=p.valor_unitario, valor_total=p.valor_total, regra_origem=p.regra_origem)
                for ad in porta.adicionais.all():
                    PortaAdicional.objects.create(porta=nova_porta, produto=ad.produto, quantidade=ad.quantidade, valor_unitario=ad.valor_unitario, valor_total=ad.valor_total, regra_origem=ad.regra_origem, lado=ad.lado)
            messages.success(request, "Orçamento clonado com sucesso!")
            if next_url:
                return redirect(next_url)
            else:
                 return redirect('/orcamentos/lista/?s=' + str(novo.id))
        portas_json = []
        for porta in orcamento.portas.all():
            portas_json.append({"numero": porta.numero, "largura": float(porta.largura), "altura": float(porta.altura), "qtd_lam": float(porta.qtd_lam or 0), "m2": float(porta.m2 or 0),
                "larg_corte": float(porta.larg_corte or 0), "alt_corte": float(porta.alt_corte or 0), "rolo": float(porta.rolo or 0), "peso": float(porta.peso or 0),
                "ft_peso": float(porta.fator_peso or 0), "eix_mot": float(porta.eixo_motor or 0), "tipo_lamina": porta.tp_lamina, "tipo_vao": porta.tp_vao,
                # 🔥 PRODUTOS NORMAIS
                "produtos": [{"codProd": pp.produto.id, "qtdProd": float(pp.quantidade), "regra_origem": pp.regra_origem} for pp in porta.produtos.all()],
                "adicionais": [{"codProd": adc.produto.id, "qtdProd": float(adc.quantidade), "lado": adc.lado, "regra_origem": adc.regra_origem,
                        "vl_unit": float(adc.valor_unitario or 0), "vl_total": float(adc.valor_total or 0),} for adc in porta.adicionais.all()]
            })
        form = OrcamentoForm(instance=orcamento, empresa=request.user.empresa, user=request.user)
    except ObjectDoesNotExist:
        error_messages.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {str(e)}")
    except DatabaseError as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except Exception as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return render(request, "orcamentos/clonar_orcamento.html",{"form": form, "orcamento": orcamento, "error_messages": error_messages, "portas": orcamento.portas.all(), "portas_json": json.dumps(portas_json)})

@login_required
@require_POST
def del_orcamento(request, id):
    if not request.user.has_perm('orcamentos.delete_orcamento'):
        messages.info(request, 'Você não tem permissão para deletar orçamentos.')
        return redirect('lista-orcamentos')
    o = get_object_or_404(Orcamento, pk=id, vinc_emp=request.user.empresa)
    if o.situacao in ['Faturado', 'Cancelado']:
        messages.warning(request, 'Orçamentos só podem ser deletados com situação Aberto!')
        return redirect('lista-orcamentos')
    o.delete()
    messages.success(request, 'Orçamento deletado com sucesso!')
    return redirect('lista-orcamentos')

@require_POST
@login_required
@transaction.atomic
def faturar_orcamento(request, id):
    orcamento = get_object_or_404(
        Orcamento.objects.select_related('cli', 'vinc_fil', 'vinc_emp').prefetch_related('formas_pgto__formas_pgto', 'portas__produtos__produto', 'portas__adicionais__produto',),
        pk=id, vinc_emp=request.user.empresa)
    if not request.user.has_perm('orcamentos.faturar_orcamento'):
        messages.error(request, 'Você não tem permissão para faturar orçamentos!')
        return redirect('/orcamentos/lista/')
    if orcamento.situacao == 'Faturado':
        messages.warning(request, 'Orçamento já está faturado!')
        return redirect('/orcamentos/lista/')
    formas = list(orcamento.formas_pgto.all())
    if not formas:
        messages.error(request, 'Informe ao menos uma forma de pagamento antes de faturar.')
        return redirect('/orcamentos/lista/')
    formas_map = {f.formas_pgto_id: f for f in formas}
    tem_forma_com_parcela = any(f.formas_pgto.gera_parcelas for f in formas)
    preview_json = request.POST.get('preview_contas_json', '').strip()
    contas_validas = []
    totais_por_forma = {}
    if tem_forma_com_parcela:
        if not preview_json:
            messages.error(request, 'A pré-visualização das contas a receber não foi enviada.')
            return redirect('/orcamentos/lista/')
        try:
            preview_contas = json.loads(preview_json)
        except json.JSONDecodeError:
            messages.error(request, 'Erro ao ler a pré-visualização das contas a receber.')
            return redirect('/orcamentos/lista/')
        if not isinstance(preview_contas, list) or not preview_contas:
            messages.error(request, 'Nenhuma conta a receber foi informada.')
            return redirect('/orcamentos/lista/')
        for i, item in enumerate(preview_contas, start=1):
            try:
                forma_pgto_id = int(item.get('forma_pgto_id'))
            except (TypeError, ValueError):
                messages.error(request, f'Parcela {i}: forma de pagamento inválida.')
                return redirect('/orcamentos/lista/')
            if forma_pgto_id not in formas_map:
                messages.error(request, f'Parcela {i}: forma de pagamento inexistente.')
                return redirect('/orcamentos/lista/')
            forma_orc = formas_map[forma_pgto_id]
            if not forma_orc.formas_pgto.gera_parcelas:
                messages.error(request, f'A forma {forma_orc.formas_pgto.descricao} não pode gerar parcelas.')
                return redirect('/orcamentos/lista/')
            # número da conta
            num_conta = (item.get('num_conta') or '').strip()
            if not num_conta:
                messages.error(request, f'Parcela {i}: número da conta não informado.')
                return redirect('/orcamentos/lista/')
            # valor
            try:
                valor = Decimal(str(item.get('valor', '0'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            except InvalidOperation:
                messages.error(request, f'Parcela {i}: valor inválido.')
                return redirect('/orcamentos/lista/')
            if valor <= 0:
                messages.error(request, f'Parcela {i}: valor deve ser maior que zero.')
                return redirect('/orcamentos/lista/')
            data_str = item.get('data_vencimento')
            try:
                if '/' in data_str:
                    data_vencimento = datetime.strptime(data_str, '%d/%m/%Y').date()
                else:
                    data_vencimento = datetime.strptime(data_str, '%Y-%m-%d').date()
            except (TypeError, ValueError):
                messages.error(request, f'Parcela {i}: data de vencimento inválida.')
                return redirect('/orcamentos/lista/')
            totais_por_forma.setdefault(forma_pgto_id, Decimal('0.00'))
            totais_por_forma[forma_pgto_id] += valor
            contas_validas.append({"forma_pgto_id": forma_pgto_id, "num_conta": num_conta.upper(), "valor": valor, "data_vencimento": data_vencimento})
        for forma in formas:
            if forma.formas_pgto.gera_parcelas:
                total_preview = totais_por_forma.get(forma.formas_pgto_id, Decimal('0.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                valor_forma = Decimal(forma.valor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                if total_preview != valor_forma:
                    messages.error(request, f'A soma das parcelas da forma {forma.formas_pgto.descricao} - ({total_preview}) difere do valor informado ({valor_forma}).')
                    return redirect('/orcamentos/lista/?s=' + str(orcamento.id))
        for conta in contas_validas:
            ContaReceber.objects.create(vinc_emp=orcamento.vinc_emp, vinc_fil=orcamento.vinc_fil, orcamento=orcamento, cliente=orcamento.cli, forma_pgto_id=conta["forma_pgto_id"],
                num_conta=conta["num_conta"], valor=conta["valor"], data_vencimento=conta["data_vencimento"], situacao='Aberta',)
    orcamento.situacao = 'Faturado'
    orcamento.dt_fat = datetime.now()
    orcamento.save(update_fields=['situacao', 'dt_fat'])
    for porta in orcamento.portas.all():
        for item in porta.produtos.all():
            produto = item.produto
            produto.estoque_prod -= item.quantidade
            produto.save(update_fields=['estoque_prod'])
        for item in porta.adicionais.all():
            produto = item.produto
            produto.estoque_prod -= item.quantidade
            produto.save(update_fields=['estoque_prod'])
    messages.success(request, f'Orçamento {orcamento.num_orcamento} faturado com sucesso!')
    return redirect('/orcamentos/lista/?s=' + str(orcamento.id))

@require_POST
@login_required
@transaction.atomic
def cancelar_orcamento(request, id):
    orcamento = get_object_or_404(
        Orcamento.objects.prefetch_related('portas__produtos__produto','portas__adicionais__produto'), pk=id, vinc_emp=request.user.empresa)
    if not request.user.has_perm('orcamentos.cancelar_orcamento'):
        messages.info(request, 'Você não tem permissão para cancelar orçamentos!')
        return redirect('/orcamentos/lista/')
    motivo = request.POST.get('motivo', '').strip()
    if not motivo:
        messages.info(request, 'Motivo do cancelamento é obrigatório!')
        return redirect('/orcamentos/lista/')
    if orcamento.situacao == 'Faturado':
        contas_pagas = ContaReceber.objects.filter(orcamento=orcamento, vinc_emp=orcamento.vinc_emp, vinc_fil=orcamento.vinc_fil, situacao='Paga').exists()
        if contas_pagas:
            messages.error(request, 'Não é possível cancelar: existem contas já recebidas.')
            return redirect('/orcamentos/lista/?s=' + str(orcamento.id))
        ContaReceber.objects.filter(orcamento=orcamento, vinc_emp=orcamento.vinc_emp, vinc_fil=orcamento.vinc_fil, situacao='Aberta').delete()
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
        return redirect('/orcamentos/lista/?s=' + str(orcamento.id))

@login_required
@require_POST
def alterar_status_orcamento(request):
    try:
        orc_id = request.POST.get("id")
        novo_status = request.POST.get("status")
        if not orc_id or not novo_status:
            return JsonResponse({"status": "erro", "mensagem": "Dados inválidos"}, status=400)
        orc = get_object_or_404(Orcamento, pk=orc_id, vinc_emp=request.user.empresa)
        orc.status = novo_status
        orc.save(update_fields=["status"])
        return JsonResponse({"status": "ok","mensagem": "Status atualizado com sucesso!"})
    except Exception as e:
        return JsonResponse({"status": "erro","mensagem": str(e)}, status=500)

@login_required
def imprimir_comprovante(request, id):
    orcamento = get_object_or_404(Orcamento, pk=id, vinc_emp=request.user.empresa)
    # Pegando todas as formas de pagamento relacionadas
    formas_pgto = orcamento.formas_pgto.all()
    # Criando uma lista de formas convertidas para uso no template
    orcamento.formas_convertidas = [{"id": f.id, "descricao": f.formas_pgto.descricao if hasattr(f, 'formas_pgto') else str(f), "valor": float(f.valor)} for f in formas_pgto]
    return render(request, 'orcamentos/comprovante.html', {'orcamento': orcamento, 'formas_pgto': formas_pgto,})

segoe_ui_bold = os.path.join(settings.BASE_DIR, "static", "fonts", "segoe-ui-bold.ttf")
segoe_ui = os.path.join(settings.BASE_DIR, "static", "fonts", "Segoe UI.ttf")
arial_narrow_bold = os.path.join(settings.BASE_DIR, "static", "fonts", "arialnarrow_bold.ttf")
times = os.path.join(settings.BASE_DIR, "static", "fonts", "Times.ttf")
times_bold = os.path.join(settings.BASE_DIR, "static", "fonts", "Times_Bold.ttf")
times_bold_italic = os.path.join(settings.BASE_DIR, "static", "fonts", "Times-Bold-Italic.ttf")

@login_required
def imprimir_comp_a4(request, id):
    orcamento = get_object_or_404(Orcamento, pk=id, vinc_emp=request.user.empresa)
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
    dados_filial = [filial.fantasia.upper(), filial.cnpj, f"{filial.endereco.upper()}, {filial.numero} - {filial.bairro_fil}", filial.cidade_fil, filial.tel]
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
    col_1 = [("Nº Orçamento:", orcamento.num_orcamento), ("Dt. Emissão:", orcamento.dt_emi.strftime("%d/%m/%Y")),
        ("Solicitante:", orcamento.nome_solicitante), ("Razão Social:", orcamento.cli.razao_social),
        ("Cliente:", f"{orcamento.cli.id} - {orcamento.nome_cli}"), ("Endereço:", f"{orcamento.cli.endereco}, Nº {orcamento.cli.numero}"),
        ("CPF/CNPJ:", orcamento.cli.cpf_cnpj),
    ]
    col_2 = [("Bairro:", orcamento.cli.bairro), ("Cidade:", orcamento.cli.cidade), ("UF:", orcamento.cli.uf), ("E-mail:", orcamento.cli.email),]
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
    totais = [("SUBTOTAL", orcamento.subtotal), ("DESCONTO", orcamento.desconto), ("ACRÉSCIMO", orcamento.acrescimo), ("TOTAL", orcamento.total),]
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

@login_required
def pdf_contrato_html(request, id):
    o = Orcamento.objects.prefetch_related('portas__produtos__produto', 'portas__adicionais__produto').get(pk=id, vinc_emp=request.user.empresa)
    portas = o.portas.all().order_by('numero')
    formas_pgto = o.formas_pgto.all()
    linhas_formas = max(formas_pgto.count(), 4)
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
    html_string = render_to_string('orcamentos/pdf_contrato.html', {'o': o, 'portas': portas, 'linhas_formas': linhas_formas, 'logo_base64': logo_base64})
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = (f'inline; filename="CONTRATO ORÇAMENTO PORTA ENROLAR - {o.num_orcamento}.pdf"')
    return response

def img_base64(path):
    if not path: return None
    if not os.path.exists(path): return None
    with Image.open(path) as img:
        if img.mode in ('RGBA', 'LA'):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        else: img = img.convert("RGB")
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=75)
        return base64.b64encode(buffer.getvalue()).decode()

@login_required
def pdf_proposta_html(request, id):
    o = Orcamento.objects.get(pk=id, vinc_emp=request.user.empresa)
    portas = o.portas.all().order_by('numero')
    for porta in portas:
        porta.tem_portinhola = porta.adicionais.filter(produto__desc_prod__iexact="PORTINHOLA", quantidade__gte=1).exists()
        porta.tem_alcapao = porta.adicionais.filter(produto__desc_prod__icontains="ALCAP", quantidade__gte=1).exists()
    lg_emp = img_base64(o.vinc_fil.logo.path)
    finders.find('img/telefone.png')
    icone_tel = finders.find('img/telefone.png')
    icone_email = finders.find('img/email.png')
    icone_loc = finders.find('img/local.png')
    ic_t = img_base64(icone_tel)
    ic_e = img_base64(icone_email)
    ic_l = img_base64(icone_loc)
    dez_p = o.total * Decimal('0.10')
    vl_tot_dsct = o.total - dez_p
    vl_tot_p_s = o.total + o.vl_p_s
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    dt_format = o.dt_emi.strftime('%d de %B de %Y').upper()
    html = render_to_string('orcamentos/pdf_proposta.html', {'o': o, 'lg_emp': lg_emp, 'portas': portas, 'vl_tot_p_s': vl_tot_p_s, 'vl_tot_dsct': vl_tot_dsct, 'ic_t': ic_t, 'ic_e': ic_e, 'ic_l': ic_l, 'dt_format': dt_format})
    pdf = HTML(string=html).write_pdf()
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = ( f'inline; filename="PROPOSTA COMERCIAL - {o.num_orcamento}.pdf"' )
    return response

@login_required
def pdf_orcamento_html(request, id):
    o = Orcamento.objects.prefetch_related(Prefetch('portas__produtos', queryset=PortaProduto.objects.select_related('produto').order_by('produto__desc_prod')), Prefetch('portas__adicionais',queryset=PortaAdicional.objects.select_related('produto').order_by('produto__desc_prod'))).get(pk=id, vinc_emp=request.user.empresa)
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
    html = render_to_string('orcamentos/pdf_orcamento.html', {'o': o, 'portas': portas, 'linhas_formas': linhas_formas, 'logo_base64': logo_base64}, request=request)
    pdf = HTML(string=html, base_url=request.build_absolute_uri('/') ).write_pdf( stylesheets=[CSS(string=""" @page {size: A4; margin: 25mm 15mm 20mm 15mm;} body {font-family: Arial, sans-serif; font-size: 11px;} """)])
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = (f'inline; filename="ORÇAMENTO PORTA ENROLAR - {o.num_orcamento}.pdf"')
    return response

@login_required
def pdf_producao_html(request, id):
    o = get_object_or_404(
        Orcamento.objects.select_related('vinc_fil','cli','solicitante',).prefetch_related(Prefetch('portas__produtos', queryset=PortaProduto.objects.select_related('produto').order_by('produto__desc_prod')), Prefetch('portas__adicionais',queryset=PortaAdicional.objects.select_related('produto').exclude(produto__especifico='Serviço/Transporte').order_by('produto__desc_prod')), 'portas',), pk=id, vinc_emp=request.user.empresa)
    portas = o.portas.all().order_by('numero')
    logo_base64 = None
    if o.vinc_fil and o.vinc_fil.logo:
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
    context = {'o': o, 'portas': portas, 'logo_base64': logo_base64,}
    html = render_to_string('orcamentos/pdf_producao.html', context, request=request)
    pdf = HTML(string=html, base_url=request.build_absolute_uri('/')).write_pdf(
        stylesheets=[CSS(string="""
                @page {size: A4; margin: 12mm 10mm 12mm 10mm;
                }
                body {font-family: Arial, Helvetica, sans-serif; font-size: 11px; color: #111;}
            """)])
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = (f'inline; filename="ORDEM DE PRODUCAO PORTA ENROLAR - {o.num_orcamento}.pdf"')
    return response