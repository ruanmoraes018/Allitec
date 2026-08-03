from datetime import datetime, timedelta, time
from decimal import Decimal
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Orcamento, OrcamentoFormaPgto, PortaOrcamento, PortaProduto, PortaAdicional, SolicitacaoPermissao, PortaOrcamentoFoto
from formas_pgto.models import FormaPgto
from .forms import OrcamentoForm, PortaAdicionalForm, PortaProdutoForm, PortaOrcamentoForm
import unicodedata
from django.http import JsonResponse
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
from notifications.models import Notification
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
from django.db.models import Prefetch, Exists, OuterRef, Count, Sum, Q
from django.db import DatabaseError, IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from util.parse_decimal import parse_decimal
from django.db.models import F
from collections import defaultdict
from core.pagamentos.fluxo import gerar_pagamentos_orcamento
from pedidos.models import Pagamento
from django.contrib.contenttypes.models import ContentType
from util.logs import gerar_alteracoes, registrar_log
from util.filiais import aplicar_filtro_filial
from fornecedores.models import Fornecedor
import calendar

PortaFormSet = inlineformset_factory(Orcamento, PortaOrcamento, form=PortaOrcamentoForm, extra=1, can_delete=False)
ProdutoFormSet = inlineformset_factory(PortaOrcamento, PortaProduto, form=PortaProdutoForm, extra=1, can_delete=True)
AdicionalFormSet = inlineformset_factory(PortaOrcamento, PortaAdicional, form=PortaAdicionalForm, extra=1, can_delete=True)

@login_required
@require_POST
def enviar_solicitacao(request):
    acao = request.POST.get('acao')
    usuario_destino_id = request.POST.get('usuario_id')
    modulo = request.POST.get('modulo')
    registro_desc = request.POST.get('registro_desc')
    if not usuario_destino_id: return JsonResponse({'error': 'ID do usuário destino não enviado.'}, status=400)
    usuario_logado = request.user
    empresa = usuario_logado.empresa
    try: usuario_destino = Usuario.objects.get(codigo_local=usuario_destino_id, empresa=empresa)
    except Usuario.DoesNotExist: return JsonResponse({'error': 'Usuário destino não encontrado.'}, status=404)
    expiracao = timezone.now() + timedelta(minutes=3)
    solicitacao = SolicitacaoPermissao.objects.create(vinc_emp=empresa, solicitante=usuario_logado, autorizado_por=usuario_destino, acao=acao, expira_em=expiracao)
    data_formatada = timezone.localtime(solicitacao.expira_em).strftime('%d/%m/%Y %H:%M')
    descricao = (
        f"{usuario_logado.first_name} solicitou liberação para "
        f"{acao.replace('_', ' ')} no módulo {modulo}. "
        f"Registro: {registro_desc}"
    )
    notify.send(usuario_logado, recipient=usuario_destino, verb=f"Solicitação de Permissão ID {solicitacao.codigo} - {data_formatada}", description=descricao,
        data={'tipo': 'SOLICITACAO', 'solicitacao_id': solicitacao.codigo}
    )
    return JsonResponse({'status': 'enviado', 'id': solicitacao.codigo, 'expira_em': solicitacao.expira_em.isoformat()})

@login_required
def verificar_status_solicitacao(request, solicitacao_id):
    try: solicitacao = SolicitacaoPermissao.objects.get(codigo=solicitacao_id, vinc_emp=request.user.empresa)
    except SolicitacaoPermissao.DoesNotExist: return JsonResponse({'status': 'nao_encontrada'})
    if timezone.now() > solicitacao.expira_em and solicitacao.status == 'Pendente':
        solicitacao.status = 'Expirada'
        solicitacao.save(update_fields=['status'])
    return JsonResponse({'status': solicitacao.status})

@login_required
@require_POST
def responder_solicitacao(request):
    solicitacao_id = request.POST.get('id')
    acao = request.POST.get('acao')
    if not solicitacao_id: return JsonResponse({'error': 'ID da solicitação não enviado'}, status=400)
    try: solicitacao = SolicitacaoPermissao.objects.get(codigo=solicitacao_id, vinc_emp=request.user.empresa, autorizado_por=request.user)
    except SolicitacaoPermissao.DoesNotExist: return JsonResponse({'error': 'Solicitação não encontrada'}, status=404)
    if timezone.now() > solicitacao.expira_em and solicitacao.status == 'Pendente':
        solicitacao.status = 'Expirada'
        solicitacao.save(update_fields=['status'])
        Notification.objects.filter(recipient=solicitacao.autorizado_por, verb__icontains=f'ID {solicitacao.codigo}', unread=True).update(unread=False)
        return JsonResponse({'status': 'Expirada'})
    if acao == 'aprovar': solicitacao.status = 'Aprovada'
    elif acao == 'negar': solicitacao.status = 'Negada'
    else: return JsonResponse({'error': 'Ação inválida'}, status=400)
    solicitacao.save(update_fields=['status'])
    Notification.objects.filter(recipient=solicitacao.autorizado_por, verb__icontains=f'ID {solicitacao.codigo}', unread=True).update(unread=False)
    return JsonResponse({'status': solicitacao.status})

@login_required
def usuarios_com_permissao(request):
    usuario_logado = request.user
    usuarios = Usuario.objects.filter(empresa=usuario_logado.empresa, gerar_senha_lib=True).order_by('codigo_local')
    lista = [{'codigo_local': u.codigo_local, 'username': u.username, 'nome': u.get_full_name() or u.username} for u in usuarios]
    return JsonResponse({'usuarios': lista})

@login_required
@require_POST
def liberar_com_senha(request):
    usuario_id = request.POST.get('usuario_id')
    senha = request.POST.get('senha')
    if not usuario_id or not senha: return JsonResponse({'status': 'erro'}, status=400)
    try: autorizador = Usuario.objects.get(codigo_local=usuario_id, empresa=request.user.empresa, gerar_senha_lib=True)
    except Usuario.DoesNotExist: return JsonResponse({'status': 'erro'}, status=404)
    if not check_password(senha, autorizador.senha_liberacao): return JsonResponse({'status': 'senha_incorreta'})
    return JsonResponse({'status': 'Aprovada'})

@login_required
@require_POST
def expirar_solicitacao(request):
    try: solicitacao = SolicitacaoPermissao.objects.get(codigo=request.POST.get('id'), vinc_emp=request.user.empresa)
    except SolicitacaoPermissao.DoesNotExist: return JsonResponse({'status': 'nao_encontrada'})
    if solicitacao.status == 'Pendente':
        solicitacao.status = 'Expirada'
        solicitacao.save(update_fields=['status'])
        Notification.objects.filter(recipient=solicitacao.autorizado_por, verb__icontains=f'ID {solicitacao.codigo}', unread=True).update(unread=False)
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
    orcamentos = (Orcamento.objects.filter(vinc_emp=request.user.empresa).select_related('cli', 'vinc_fil', 'solicitante').prefetch_related('formas_pgto__formas_pgto')).annotate(
        tem_forma_com_parcela=Exists(formas_com_parcela))
    # Aplica a regra de acesso às filiais
    orcamentos, aguardando_filial = aplicar_filtro_filial(request, orcamentos)
    if s: orcamentos = orcamentos.filter(codigo__iexact=s)
    if por_dt == 'Sim' and dt_ini and dt_fim:
        try:
            dt_ini_dt = datetime.combine(datetime.strptime(dt_ini, '%d/%m/%Y').date(), time.min)
            dt_fim_dt = datetime.combine(datetime.strptime(dt_fim, '%d/%m/%Y').date(), time.max)
            if tp_dt == 'Emissão': orcamentos = orcamentos.filter(dt_emi__range=(dt_ini_dt, dt_fim_dt))
            elif tp_dt == 'Entrega': orcamentos = orcamentos.filter(dt_ent__range=(dt_ini_dt, dt_fim_dt))
            elif tp_dt == 'Fatura': orcamentos = orcamentos.filter(dt_fat__range=(dt_ini_dt, dt_fim_dt))
        except ValueError: orcamentos = Orcamento.objects.none()
    filtros_ativos = any([s, f_s, por_dt == 'Sim', cli, tec, tp_dt and tp_dt != 'Todos'])
    if not filtros_ativos and not aguardando_filial: orcamentos = orcamentos.filter(dt_emi__range=(inicio_dia, fim_dia), situacao='Aberto')
    if f_s and f_s != 'Todos': orcamentos = orcamentos.filter(situacao=f_s)
    if cli: orcamentos = orcamentos.filter(cli__codigo=cli)
    if tec: orcamentos = orcamentos.filter(solicitante__codigo=tec)
    if ordem == '0': orcamentos = orcamentos.order_by('codigo')
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
    orc_ab_pg = sum(1 for o in orcamentos.object_list if o.situacao == 'Aberto')
    orc_fat_pg = sum(1 for o in orcamentos.object_list if o.situacao == 'Faturado')
    orc_canc_pg = sum(1 for o in orcamentos.object_list if o.situacao == 'Cancelado')
    tot_ab_pg = sum((o.total or Decimal('0.00')) for o in orcamentos.object_list if o.situacao == 'Aberto')
    tot_fat_pg = sum((o.total or Decimal('0.00')) for o in orcamentos.object_list if o.situacao == 'Faturado')
    tot_canc_pg = sum((o.total or Decimal('0.00')) for o in orcamentos.object_list if o.situacao == 'Cancelado')
    return render(request, 'orcamentos/lista.html', {
    'orcamentos': orcamentos, 's': s, 'sit': f_s, 'fil': fil, 'cli': cli, 'tec': tec, 'dt_ini': dt_ini, 'dt_fim': dt_fim, 'p_dt': por_dt, 'tp_dt': tp_dt, 'reg': reg, 'ordem': ordem,
    'filiais': Filial.objects.filter(vinc_emp=request.user.empresa), 'clientes': Cliente.objects.filter(vinc_emp=request.user.empresa), 'tecnicos': Tecnico.objects.filter(vinc_emp=request.user.empresa),
    'tot_ab': tot_ab_pg, 'tot_fat': tot_fat_pg, 'tot_canc': tot_canc_pg, 'orc_ab': orc_ab_pg, 'orc_fat': orc_fat_pg, 'orc_canc': orc_canc_pg,
})

KANBAN_MODOS = {
    "Aberto": {"colunas": ["Aguardando Aprovação", "Em Análise", "Aprovado", "Recusado"], "campo": "ocasiao", "icones": {
        "Aguardando Aprovação": "bi-hourglass-split", "Em Análise": "bi-search", "Aprovado": "bi-check-circle-fill", "Recusado": "bi-x-circle-fill",},},
    "Faturado": {"colunas": ["Em Produção", "Embalada", "Entregue", "Instalada"], "campo": "status", "icones": {
        "Em Produção": "bi-gear-fill", "Embalada": "bi-box-fill", "Entregue": "bi-truck", "Instalada": "bi-tools",},},
}
def parse_date_input(valor):
    if not valor: return ""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try: return datetime.strptime(valor, fmt).strftime("%Y-%m-%d")
        except ValueError: continue
    return ""

def parse_date_filter(valor):
    if not valor: return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try: return datetime.strptime(valor, fmt).date()
        except ValueError: continue
    return None

@login_required
def kanban_orcamentos(request):
    empresa = request.user.empresa
    situacao_ativa = request.GET.get("situacao", "Aberto")
    if situacao_ativa not in KANBAN_MODOS: situacao_ativa = "Aberto"
    modo = KANBAN_MODOS[situacao_ativa]
    # COMBOS
    clientes    = Cliente.objects.filter(vinc_emp=empresa).only("codigo", "fantasia").order_by("fantasia")
    solicitantes= Tecnico.objects.filter(vinc_emp=empresa).only("codigo", "nome").order_by("nome")
    fornecedores= Fornecedor.objects.filter(vinc_emp=empresa).only("codigo", "fantasia").order_by("fantasia")
    filiais     = Filial.objects.filter(vinc_emp=empresa).only("codigo", "fantasia").order_by("fantasia")
    # FILTROS
    filtros = {
        "cliente": request.GET.get("cliente", ""), "solicitante": request.GET.get("solicitante", ""), "fornecedor": request.GET.get("fornecedor", ""),
        "filial": request.GET.get("filial", ""), "situacao": situacao_ativa, "status": request.GET.get("status", ""), "ocasiao": request.GET.get("ocasiao", ""),
        "prioridade": request.GET.get("prioridade", ""), "tipo_entrega": request.GET.get("tipo_entrega", ""), "pesquisa": request.GET.get("pesquisa", "").strip(),
        "dt_inicial": parse_date_input(request.GET.get("dt_inicial", "")), "dt_final": parse_date_input(request.GET.get("dt_final", "")),
        "entrega_inicial": parse_date_input(request.GET.get("entrega_inicial", "")), "entrega_final": parse_date_input(request.GET.get("entrega_final", "")),
        "instalacao_inicial": parse_date_input(request.GET.get("instalacao_inicial", "")), "instalacao_final": parse_date_input(request.GET.get("instalacao_final", "")),
        "valor_min": request.GET.get("valor_min", ""), "valor_max": request.GET.get("valor_max", ""), "ordenacao": request.GET.get("ordenacao", "prioridade"),
    }
    # RESUMO — sempre mostra totais dos dois modos no topo
    resumo_faturado = Orcamento.objects.filter(vinc_emp=empresa, situacao="Faturado").aggregate(quantidade=Count("codigo"), total=Sum("total"),
        urgente=Count("codigo", filter=Q(prioridade="Urgente")), alta=Count("codigo", filter=Q(prioridade="Alta")), normal=Count("codigo", filter=Q(prioridade="Normal")),
    )
    if resumo_faturado["total"] is None: resumo_faturado["total"] = Decimal("0.00")
    resumo_aberto = Orcamento.objects.filter(vinc_emp=empresa, situacao="Aberto").aggregate(quantidade=Count("codigo"), total=Sum("total"),)
    if resumo_aberto["total"] is None: resumo_aberto["total"] = Decimal("0.00")
    # CONTADORES POR COLUNA do modo ativo (antes do AJAX)
    contadores = {}
    for col in modo["colunas"]:
        filtro_col = {f"vinc_emp": empresa, "situacao": situacao_ativa, modo["campo"]: col}
        dados = Orcamento.objects.filter(**filtro_col).aggregate(quantidade=Count("codigo"), total=Sum("total"))
        contadores[col] = {"quantidade": dados["quantidade"] or 0, "total": dados["total"] or Decimal("0.00"),}
    # DATA VISÍVEL
    if request.GET.get("dt_inicial") or request.GET.get("dt_final"): tipo_data_ativo = "emissao"
    elif request.GET.get("entrega_inicial") or request.GET.get("entrega_final"): tipo_data_ativo = "entrega"
    elif request.GET.get("instalacao_inicial") or request.GET.get("instalacao_final"): tipo_data_ativo = "instalacao"
    else: tipo_data_ativo = "emissao"
    data_ini_visivel = filtros.get("dt_inicial") or filtros.get("entrega_inicial") or filtros.get("instalacao_inicial") or ""
    data_fim_visivel = filtros.get("dt_final")   or filtros.get("entrega_final")   or filtros.get("instalacao_final")   or ""
    context = {
        "clientes": clientes, "solicitantes": solicitantes, "fornecedores": fornecedores, "filiais": filiais, "filtros": filtros, "situacoes": list(KANBAN_MODOS.keys()),
        "situacao_ativa": situacao_ativa, "modo": modo, "status_list":  modo["colunas"], "prioridades": ["Normal", "Alta", "Urgente"],
        "tipos_entrega":["Retirada", "Entrega", "Entrega e Instalação"],
        "ordenacoes": {
            "prioridade": "Prioridade", "mais_recentes": "Mais recentes", "mais_antigos": "Mais antigos", "cliente": "Cliente",
            "maior_valor": "Maior valor", "menor_valor": "Menor valor", "entrega": "Entrega", "instalacao": "Instalação", "status": "Status",
        },
        "contadores":contadores,"resumo_faturado":resumo_faturado,"resumo_aberto": resumo_aberto, "tipo_data_ativo": tipo_data_ativo, "data_ini_visivel": data_ini_visivel,
        "data_fim_visivel": data_fim_visivel, "refresh_seconds": 30,
    }
    return render(request, "orcamentos/kanban.html", context)

@login_required
def kanban_dados(request):
    empresa = request.user.empresa
    situacao_ativa = request.GET.get("situacao", "Aberto")
    if situacao_ativa not in KANBAN_MODOS: situacao_ativa = "Aberto"
    modo = KANBAN_MODOS[situacao_ativa]
    STATUS = modo["colunas"]
    campo_coluna = modo["campo"]   # "status" ou "ocasiao"
    qs = (Orcamento.objects.filter(vinc_emp=empresa).select_related("cli", "solicitante", "fornecedor", "vinc_fil", "tabela_preco")
        .prefetch_related(Prefetch("portas", queryset=(PortaOrcamento.objects.select_related().prefetch_related("fotos", "produtos__produto", "adicionais__produto"))), "formas_pgto",)
        .annotate(qtd_portas=Count("portas",distinct=True),qtd_produtos=Count("portas__produtos",distinct=True),qtd_adicionais=Count("portas__adicionais",distinct=True),)
    )
    # FILTRO DE DATA PADRÃO — mês atual, só para modo Aberto
    nenhuma_data = not any([request.GET.get("dt_inicial"), request.GET.get("dt_final"), request.GET.get("entrega_inicial"), request.GET.get("entrega_final"),
        request.GET.get("instalacao_inicial"), request.GET.get("instalacao_final"),
    ])
    if nenhuma_data and situacao_ativa == "Aberto":
        hoje = timezone.localdate()
        inicio_mes = datetime.combine(hoje.replace(day=1), time.min)
        fim_mes = datetime.combine(hoje.replace(day=calendar.monthrange(hoje.year, hoje.month)[1]), time.max)
        qs = qs.filter(dt_emi__range=(inicio_mes, fim_mes))
    # PESQUISA
    pesquisa = request.GET.get("pesquisa", "").strip()
    if pesquisa:
        qs = qs.filter(Q(codigo__icontains=pesquisa) | Q(num_orcamento__icontains=pesquisa) | Q(nome_cli__icontains=pesquisa) | Q(nome_solicitante__icontains=pesquisa) |
            Q(nome_fornecedor__icontains=pesquisa) | Q(obs_cli__icontains=pesquisa)
        )
    # FILIAL
    filial = request.GET.get("filial")
    if filial: qs = qs.filter(vinc_fil__codigo=filial)
    # CLIENTE
    cliente = request.GET.get("cliente")
    if cliente: qs = qs.filter(cli__codigo=cliente)
    # SOLICITANTE
    solicitante = request.GET.get("solicitante")
    if solicitante: qs = qs.filter(solicitante__codigo=solicitante)
    # FORNECEDOR
    fornecedor = request.GET.get("fornecedor")
    if fornecedor: qs = qs.filter(fornecedor__codigo=fornecedor)
    # SITUAÇÃO — sempre filtra pelo modo ativo
    qs = qs.filter(situacao=situacao_ativa)
    # PRIORIDADE
    prioridade = request.GET.get("prioridade")
    if prioridade: qs = qs.filter(prioridade=prioridade)
    # TIPO ENTREGA
    entrega = request.GET.get("tipo_entrega")
    if entrega: qs = qs.filter(tipo_entrega=entrega)
    dt_ini = parse_date_filter(request.GET.get("dt_inicial"))
    dt_fim = parse_date_filter(request.GET.get("dt_final"))
    if dt_ini and dt_fim: qs = qs.filter(dt_emi__range=(datetime.combine(dt_ini, time.min), datetime.combine(dt_fim, time.max),))
    elif dt_ini: qs = qs.filter(dt_emi__gte=datetime.combine(dt_ini, time.min))
    elif dt_fim: qs = qs.filter(dt_emi__lte=datetime.combine(dt_fim, time.max))
    # ENTREGA
    entrega_ini = parse_date_filter(request.GET.get("entrega_inicial"))
    entrega_fim = parse_date_filter(request.GET.get("entrega_final"))
    if entrega_ini and entrega_fim: qs = qs.filter(dt_ent__range=( datetime.combine(entrega_ini, time.min), datetime.combine(entrega_fim, time.max),))
    elif entrega_ini: qs = qs.filter(dt_ent__gte=datetime.combine(entrega_ini, time.min))
    elif entrega_fim: qs = qs.filter(dt_ent__lte=datetime.combine(entrega_fim, time.max))
    # INSTALAÇÃO
    inst_ini = parse_date_filter(request.GET.get("instalacao_inicial"))
    inst_fim = parse_date_filter(request.GET.get("instalacao_final"))
    if inst_ini and inst_fim: qs = qs.filter(dt_prev_instalacao__range=(datetime.combine(inst_ini, time.min), datetime.combine(inst_fim, time.max),))
    elif inst_ini: qs = qs.filter(dt_prev_instalacao__gte=datetime.combine(inst_ini, time.min))
    elif inst_fim: qs = qs.filter(dt_prev_instalacao__lte=datetime.combine(inst_fim, time.max))
    # VALORES
    minimo = request.GET.get("valor_min")
    maximo = request.GET.get("valor_max")
    if minimo: qs = qs.filter(total__gte=minimo.replace(",", "."))
    if maximo: qs = qs.filter(total__lte=maximo.replace(",", "."))
    # ATRASADOS
    if request.GET.get("atrasados") == "1": qs = qs.filter(Q(dt_ent__lt=timezone.now()) | Q(dt_prev_instalacao__lt=timezone.now())).exclude(situacao="Cancelado")
    # ORDENAÇÃO
    ordem = request.GET.get("ordenacao", "prioridade")
    ordem_map = {
        "cliente":"nome_cli","solicitante":"nome_solicitante","fornecedor":"nome_fornecedor", "maior_valor": "-total", "menor_valor": "total", "mais_recentes": "-dt_emi",
        "mais_antigos": "dt_emi", "entrega": "dt_ent", "instalacao": "dt_prev_instalacao", "prioridade": "-prioridade", "status": campo_coluna, "codigo": "-codigo",
    }
    qs = qs.order_by(ordem_map.get(ordem, "-codigo"))
    hoje = timezone.localdate()
    colunas = {}
    for st in STATUS:
        lista = []
        total_coluna = Decimal("0.00")
        for o in qs.filter(**{campo_coluna: st}):
            total_coluna += o.total or Decimal("0.00")
            fotos = peso = m2 = 0
            peso = m2 = Decimal("0.00")
            for p in o.portas.all():
                fotos += p.fotos.count()
                peso  += p.peso or Decimal("0.00")
                m2    += p.m2   or Decimal("0.00")
            atraso = dias_atraso = 0
            atraso = False
            if o.dt_ent:
                dias_atraso = (hoje - o.dt_ent.date()).days
                atraso = dias_atraso > 0
            dias_inst = None
            if o.dt_prev_instalacao: dias_inst = (o.dt_prev_instalacao.date() - hoje).days
            lista.append({
                "id": o.codigo, "codigo": o.codigo, "numero": o.num_orcamento, "cliente": o.nome_cli, "solicitante": o.nome_solicitante, "fornecedor": o.nome_fornecedor, "filial":o.fantasia_emp,"valor":o.total,
                "subtotal":o.subtotal,"status":o.status,"ocasiao":o.ocasiao,"coluna":getattr(o,campo_coluna),"situacao":o.situacao, "prioridade": o.prioridade, "tipo_entrega": o.tipo_entrega, "dt_emi": o.dt_emi,
                "dt_ent": o.dt_ent, "dt_inst": o.dt_prev_instalacao,"portas":o.qtd_portas, "produtos": o.qtd_produtos, "adicionais": o.qtd_adicionais, "peso": peso, "m2": m2, "fotos": fotos, "atrasado": atraso,
                "dias_atraso": dias_atraso, "dias_instalacao": dias_inst,
            })
        colunas[st] = {"cards": lista, "quantidade": len(lista), "valor": total_coluna}
    html = render_to_string("orcamentos/kanban_cards.html", {"colunas": colunas, "STATUS": STATUS, "modo": modo}, request=request,)
    resumo = {
        "total_orcamentos": sum(v["quantidade"] for v in colunas.values()), "portas": sum(c["portas"] for col in colunas.values() for c in col["cards"]),
        "produtos": sum(c["produtos"] for col in colunas.values() for c in col["cards"]),
    }
    return JsonResponse({"html": html, "resumo": resumo, "colunas": {k: {"quantidade": v["quantidade"], "valor": float(v["valor"])} for k, v in colunas.items()},})

@login_required
@require_POST
def alterar_status_orc_kanban(request):
    empresa      = request.user.empresa
    cod_orc      = request.POST.get("codigo")
    novo_valor   = request.POST.get("status")
    situacao_ativa = request.POST.get("situacao", "Faturado")
    if situacao_ativa not in KANBAN_MODOS: situacao_ativa = "Faturado"
    modo = KANBAN_MODOS[situacao_ativa]
    campo_coluna = modo["campo"]
    if not cod_orc: return JsonResponse({"ok": False, "erro": "Orçamento inválido."}, status=400)
    if novo_valor not in modo["colunas"]: return JsonResponse({"ok": False, "erro": "Valor inválido para este modo."}, status=400)
    try:
        with transaction.atomic():
            orc = Orcamento.objects.select_for_update().get(codigo=cod_orc, vinc_emp=empresa)
            valor_anterior = getattr(orc, campo_coluna)
            if valor_anterior == novo_valor: return JsonResponse({"ok": True, "status": novo_valor})
            setattr(orc, campo_coluna, novo_valor)
            orc.save(update_fields=[campo_coluna])
            return JsonResponse({"ok": True, "codigo": orc.codigo, "status_anterior": valor_anterior, "status": novo_valor,})
    except Orcamento.DoesNotExist: return JsonResponse({"ok": False, "erro": "Orçamento não encontrado."}, status=404)
    except Exception as e: return JsonResponse({"ok": False, "erro": str(e)}, status=500)

@login_required
def detalhes_orc_ajax(request, codigo):
    try:
        o = get_object_or_404(Orcamento.objects.prefetch_related('portas__produtos__produto__unidProd', 'portas__adicionais__produto__unidProd', 'portas__fotos'), codigo=codigo, vinc_emp=request.user.empresa)
        portas_data = []
        for porta in o.portas.all().order_by('numero'):
            produtos = []
            adicionais = []
            fotos = [{"id": foto.id, "url": foto.foto.url, "principal": foto.principal, "ordem": foto.ordem, "criado_em": foto.criado_em.strftime("%d/%m/%Y %H:%M"),} for foto in porta.fotos.all().order_by("ordem", "id")]
            contador_prod = 1
            for p in porta.produtos.all():
                produtos.append({"item": f"{contador_prod:03}", "codigo": p.produto.codigo, "produto": p.produto.desc_prod, "unidade": getattr(p.produto.unidProd, "nome_unidade", ""), "valor_unit": str(p.valor_unitario), "qtd": str(p.quantidade), "valor_total": str(p.valor_total), "regra_origem": p.regra_origem or ""})
                contador_prod += 1
            contador_adc = 1
            for a in porta.adicionais.all():
                adicionais.append({"item": f"{contador_adc:03}", "codigo": a.produto.codigo, "produto": a.produto.desc_prod, "unidade": getattr(a.produto.unidProd, "nome_unidade", ""), "valor_unit": str(a.valor_unitario), "qtd": str(a.quantidade), "valor_total": str(a.valor_total), "regra_origem": a.regra_origem or "", "lado": a.lado or ""})
                contador_adc += 1
            portas_data.append({"numero": porta.numero, "largura": str(porta.largura), "altura": str(porta.altura), "m2": str(porta.m2), "produtos": produtos, "adicionais": adicionais, "fotos": fotos, "detalhes": {
                "pintura_porta":porta.pintura_porta,"cor_porta":porta.cor_porta,"nr_serie_motor":porta.nr_serie_motor,"garantia_motor_meses":porta.garantia_motor_meses,"possui_passagem_pedestre":porta.possui_passagem_pedestre,
                "largura_passagem": str(porta.largura_passagem), "altura_passagem": str(porta.altura_passagem), "obs_porta": porta.obs_porta,
            }})
        data = {"id": o.codigo, "num_orcamento": o.num_orcamento, "serial": o.codigo, "situacao": o.situacao, "status": o.status, "data_emissao": (o.dt_emi - timedelta(hours=3)).strftime("%d/%m/%Y - %H:%M") if o.dt_emi else "", "data_entrega": o.dt_ent.strftime("%d/%m/%Y") if o.dt_ent else "", "cliente": {"nome": o.nome_cli, "empresa": {"nome": o.fantasia_emp}, "tel": getattr(o.cli, "tel", "")}, "colaborador": o.nome_solicitante, "vl_tot": str(o.total), "obs": o.obs_cli, "portas": portas_data}
        return JsonResponse(data)
    except Orcamento.DoesNotExist: return JsonResponse({'error': 'Orçamento não encontrado'}, status=404)

@login_required
def add_orcamento(request):
    empresa = request.user.empresa
    if not request.user.has_perm('orcamentos.add_orcamento'):
        messages.info(request, 'Você não tem permissão para adicionar orçamentos.')
        return redirect('/orcamentos/lista/')
    if request.method != 'POST':
        form = OrcamentoForm(empresa=empresa, user=request.user)
        return render(request, 'orcamentos/add_orcamento.html', {'form': form, 'next': request.GET.get('next', '')})
    form = OrcamentoForm(data=request.POST, files=request.FILES, empresa=empresa, user=request.user)
    if not form.is_valid():
        error_messages = [f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!" for field in form if field.errors]
        return render(request, 'orcamentos/add_orcamento.html', {'form': form, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            o = form.save(commit=False)
            if o.cli.vinc_emp != empresa: raise PermissionError("Cliente não pertence à empresa.")
            if o.vinc_fil.vinc_emp != empresa: raise PermissionError("Filial não pertence à empresa.")
            o.dt_emi = timezone.now()
            o.situacao = 'Aberto'
            o.vinc_emp = empresa
            o.save()
            o.num_orcamento = f"{timezone.now():%Y-}{o.codigo}"
            o.desconto  = parse_decimal(request.POST.get("desconto")  or "0")
            o.acrescimo = parse_decimal(request.POST.get("acrescimo") or "0")
            o.save(update_fields=['num_orcamento', 'desconto', 'acrescimo'])
            # Portas
            portas_json = request.POST.get("json_portas")
            lista_portas = []
            if portas_json:
                try: lista_portas = json.loads(portas_json)
                except json.JSONDecodeError: pass
            for p in lista_portas:
                porta = PortaOrcamento.objects.create(orcamento=o, numero=p.get("numero", 1), largura=p.get("largura") or 0, altura=p.get("altura") or 0, qtd_lam=p.get("qtd_lam") or 0, m2=p.get("m2") or 0,
                    larg_corte=p.get("larg_corte") or 0, alt_corte=p.get("alt_corte") or 0, rolo=p.get("rolo") or 0, peso=p.get("peso") or 0, fator_peso=p.get("ft_peso") or 0, eixo_motor=p.get("eix_mot") or 0,
                    tp_lamina=p.get("tipo_lamina","Fechada"),tp_vao=p.get("tipo_vao","Fora do Vão"),op_guia_e=p.get("op_guia_e","Dentro do Vão"),op_guia_d=p.get("op_guia_d","Dentro do Vão"),acabamento_guia=p.get("acabamento_guia"),
                    tp_acionamento=p.get("tp_acionamento"), lado_motor=p.get("lado_motor"), tp_mola=p.get("tp_mola"), possui_passagem_pedestre=p.get("possui_passagem_pedestre"), altura_passagem=p.get("largura_passagem"),
                    largura_passagem=p.get("altura_passagem"), obs_porta=p.get("obs_porta"), cor_porta=p.get("cor_porta"), pintura_porta=p.get("pintura_porta"), nr_serie_motor=p.get("nr_serie_motor"), garantia_motor_meses=p.get("garantia_motor_meses") or 12,
                    tp_travamento=p.get("tp_travamento"), posicao_eixo=p.get("posicao_eixo"), testeira=p.get("testeira"), tp_instalacao=p.get("tp_instalacao"), qtd_pares_trava=p.get("qtd_pares_trava"),
                )
                _salvar_produtos_porta(porta, p.get("produtos", []), empresa)
                _salvar_adicionais_porta(porta, p.get("adicionais", []), empresa)
                _salvar_fotos_porta(porta, request.FILES)
            # Subtotal
            o.atualizar_subtotal()
            if o.subtotal == 0:
                raise ValueError("O orçamento precisa ter pelo menos um item com valor.")
            o.save(update_fields=['subtotal', 'total'])
            # Formas de pagamento
            _salvar_formas_pgto(o, request.POST.get("json_formas_pgto"), empresa)
            registrar_log(request, "CRIAR", "Orçamento", o.codigo, f"Adicionou o orçamento, Nº: {o.codigo}", o.id, gerar_alteracoes(obj_novo=o))
        messages.success(request, "Orçamento criado com sucesso!")
        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url: return redirect(next_url)
        return redirect('/orcamentos/lista/?s=' + str(o.codigo))
    except PermissionError as e:
        messages.error(request, str(e))
    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f"Erro inesperado: {e}")
    form = OrcamentoForm(data=request.POST, files=request.FILES, empresa=empresa, user=request.user)
    return render(request, 'orcamentos/add_orcamento.html', {'form': form, 'error_messages': []})

@login_required
def att_orcamento(request, codigo):
    empresa = request.user.empresa
    orcamento = get_object_or_404(Orcamento.objects.prefetch_related('portas__produtos__produto', 'portas__adicionais__produto'), codigo=codigo, vinc_emp=empresa)
    if not request.user.has_perm('orcamentos.change_orcamento'):
        messages.info(request, 'Você não tem permissão para editar orçamentos.')
        return redirect('/orcamentos/lista/')
    if orcamento.situacao != 'Aberto':
        messages.warning(request, 'Somente orçamentos em Aberto podem ser editados!')
        return redirect(f'/orcamentos/lista/?s={orcamento.codigo}')
    if request.method != 'POST':
        form = OrcamentoForm(instance=orcamento, empresa=empresa, user=request.user)
        portas_json = _montar_portas_json(orcamento)
        return render(request, 'orcamentos/att_orcamento.html', {'form': form, 'orcamento': orcamento, 'portas': orcamento.portas.all(), 'portas_json': json.dumps(portas_json, default=float), 'error_messages': [],})
    form = OrcamentoForm(request.POST, request.FILES, instance=orcamento, empresa=empresa, user=request.user)
    if not form.is_valid():
        erros = [f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!" for field in form if field.errors]
        portas_json = _montar_portas_json(orcamento)
        return render(request, 'orcamentos/att_orcamento.html', {'form': form, 'orcamento': orcamento, 'error_messages': erros, 'portas': orcamento.portas.all(), 'portas_json': json.dumps(portas_json, default=float),})
    it_old = Orcamento.objects.get(codigo=orcamento.codigo)
    try:
        with transaction.atomic():
            orcamento_editado = form.save(commit=False)
            agora = timezone.localtime()
            orcamento_editado.dt_emi = datetime.combine(orcamento_editado.dt_emi.date(), agora.time())
            orcamento_editado.desconto  = parse_decimal(request.POST.get("desconto")  or "0")
            orcamento_editado.acrescimo = parse_decimal(request.POST.get("acrescimo") or "0")
            orcamento_editado.save()
            # Portas
            lista_portas = []
            portas_json_raw = request.POST.get("json_portas")
            if portas_json_raw:
                try: lista_portas = json.loads(portas_json_raw)
                except json.JSONDecodeError: pass
            lista_portas = [p for p in lista_portas if isinstance(p, dict) and p.get("largura") and p.get("altura")]
            # Preserva lados antigos
            lados_antigos = {}
            for porta_antiga in orcamento.portas.all():
                for adc in porta_antiga.adicionais.all():
                    chave = (int(porta_antiga.numero or 0), int(adc.produto.codigo or 0), str(adc.regra_origem or "").strip())
                    lados_antigos[chave] = (adc.lado or "").strip()
            portas_existentes = {p.numero: p for p in orcamento.portas.all()}
            numeros_recebidos = set()
            for p in lista_portas:
                numero = int(p.get("numero", 1))
                numeros_recebidos.add(numero)
                campos_porta = dict(largura=p.get("largura") or 0, altura=p.get("altura") or 0, qtd_lam=p.get("qtd_lam") or 0, m2=p.get("m2") or 0, larg_corte=p.get("larg_corte") or 0, alt_corte=p.get("alt_corte") or 0,
                    rolo=p.get("rolo") or 0, peso=p.get("peso") or 0, fator_peso=p.get("ft_peso") or 0, eixo_motor=p.get("eix_mot") or 0, tp_lamina=p.get("tipo_lamina", "Fechada"), tp_vao=p.get("tipo_vao", "Fora do Vão"),
                    op_guia_e=p.get("op_guia_e"), op_guia_d=p.get("op_guia_d"), acabamento_guia=p.get("acabamento_guia"), tp_acionamento=p.get("tp_acionamento"), lado_motor=p.get("lado_motor"), tp_mola=p.get("tp_mola"),
                    tp_travamento=p.get("tp_travamento"), posicao_eixo=p.get("posicao_eixo"), tp_instalacao=p.get("tp_instalacao"), testeira=p.get("testeira") or 0, qtd_pares_trava=p.get("qtd_pares_trava") or 0,
                    pintura_porta=p.get("pintura_porta"), cor_porta=p.get("cor_porta"), nr_serie_motor=p.get("nr_serie_motor"), garantia_motor_meses=p.get("garantia_motor_meses") or 12, possui_passagem_pedestre=p.get("possui_passagem_pedestre"),
                    largura_passagem=p.get("largura_passagem"), altura_passagem=p.get("altura_passagem"), obs_porta=p.get("obs_porta"),
                )
                if numero in portas_existentes:
                    porta = portas_existentes[numero]
                    for campo, valor in campos_porta.items():
                        setattr(porta, campo, valor)
                    porta.save()
                    porta.produtos.all().delete()
                    porta.adicionais.all().delete()
                else:
                    porta = PortaOrcamento.objects.create(orcamento=orcamento, numero=numero, **campos_porta)
                _salvar_produtos_porta(porta, p.get("produtos", []), empresa)
                _salvar_adicionais_porta(porta, p.get("adicionais", []), empresa, lados_antigos=lados_antigos, numero_porta=numero)
                _salvar_fotos_porta(porta, request.FILES)
            # Remove portas deletadas
            for numero, porta in portas_existentes.items():
                if numero not in numeros_recebidos:
                    porta.delete()
            orcamento.refresh_from_db()
            orcamento.atualizar_subtotal()
            if orcamento.subtotal == 0:
                raise ValueError("O orçamento precisa ter pelo menos um item com valor.")
            orcamento.save(update_fields=["subtotal", "total"])
            _salvar_formas_pgto(orcamento, request.POST.get("json_formas_pgto"), empresa, limpar_anteriores=True)
            orcamento.num_orcamento = f"{timezone.now():%Y-}{orcamento.codigo}"
            orcamento.save(update_fields=["num_orcamento"])
            registrar_log(request, "ALTERAR", "Orçamento", orcamento.codigo, f"Alterou o orçamento, Nº: {orcamento.codigo}", orcamento.id, gerar_alteracoes(it_old, orcamento))
        messages.success(request, "Orçamento atualizado com sucesso!")
        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url: return redirect(next_url)
        return redirect(f"/orcamentos/lista/?s={orcamento.codigo}")
    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f"Erro inesperado: {e}")
    portas_json = _montar_portas_json(orcamento)
    return render(request, 'orcamentos/att_orcamento.html', {'form': form, 'orcamento': orcamento, 'error_messages': [], 'portas': orcamento.portas.all(), 'portas_json': json.dumps(portas_json, default=float),})

# ── Helpers ──────────────────────────────────────────────────────────────────
def _salvar_produtos_porta(porta, produtos, empresa):
    for item in produtos:
        if not isinstance(item, dict): continue
        cod = item.get("codProd")
        if not cod: continue
        try: produto = Produto.objects.get(codigo=cod, vinc_emp=empresa)
        except Produto.DoesNotExist: continue
        qtd = Decimal(str(item.get("qtdProd") or "0"))
        vl_unit  = Decimal(str(item.get("vl_unit")  or "0"))
        vl_total = Decimal(str(item.get("vl_total") or "0"))
        if vl_total == 0 and vl_unit > 0 and qtd: vl_total = vl_unit * qtd
        PortaProduto.objects.create(porta=porta, produto=produto, quantidade=qtd, valor_unitario=vl_unit, valor_total=vl_total, regra_origem=item.get("regra_origem"))

def _salvar_adicionais_porta(porta, adicionais, empresa, lados_antigos=None, numero_porta=None):
    for item in adicionais:
        if not isinstance(item, dict): continue
        cod = item.get("codProd")
        if not cod: continue
        try: produto = Produto.objects.get(codigo=cod, vinc_emp=empresa)
        except Produto.DoesNotExist: continue
        qtd  = Decimal(str(item.get("qtdProd") or "0"))
        lado = (item.get("lado") or "").strip()
        regra_origem = item.get("regra_origem")
        if not lado and lados_antigos and numero_porta is not None:
            chave = (int(numero_porta), int(cod), str(regra_origem or "").strip())
            lado = lados_antigos.get(chave, "")
        vl_unit  = Decimal(str(item.get("vl_unit")  or "0"))
        vl_total = Decimal(str(item.get("vl_total") or "0"))
        if vl_total == 0 and vl_unit > 0 and qtd: vl_total = vl_unit * qtd
        PortaAdicional.objects.create(porta=porta, produto=produto, quantidade=qtd, valor_unitario=vl_unit, valor_total=vl_total, regra_origem=regra_origem, lado=lado)

def _salvar_fotos_porta(porta, files):
    for chave in files:
        if chave == f"fotos_{porta.numero}":
            for foto in files.getlist(chave):
                PortaOrcamentoFoto.objects.create(porta=porta, foto=foto)

def _salvar_formas_pgto(orcamento, json_str, empresa, limpar_anteriores=False):
    if not json_str: return
    if limpar_anteriores: OrcamentoFormaPgto.objects.filter(orcamento=orcamento).delete()
    try: formas = json.loads(json_str)
    except json.JSONDecodeError: return
    for f in formas:
        forma_id = f.get("forma_id")
        valor    = Decimal(str(f.get("valor") or "0"))
        parcelas = int(f.get("parcelas") or 1)
        dias     = int(f.get("dias") or 0)
        if not forma_id or valor < Decimal("0.01"): continue
        try: fp = FormaPgto.objects.get(codigo=forma_id, vinc_emp=empresa)
        except FormaPgto.DoesNotExist: continue
        OrcamentoFormaPgto.objects.create(orcamento=orcamento, formas_pgto=fp, valor=valor, parcelas=parcelas, dias_intervalo=dias)

def _montar_portas_json(orcamento):
    portas_json = []
    for p in orcamento.portas.all():
        portas_json.append({"numero": p.numero, "largura": float(p.largura), "altura": float(p.altura), "qtd_lam": float(p.qtd_lam or 0), "m2": float(p.m2 or 0), "larg_corte": float(p.larg_corte or 0), "alt_corte": float(p.alt_corte or 0),
            "rolo": float(p.rolo or 0), "peso": float(p.peso or 0), "ft_peso": float(p.fator_peso or 0), "eix_mot": float(p.eixo_motor or 0), "tipo_lamina": p.tp_lamina, "tipo_vao": p.tp_vao, "op_guia_e": p.op_guia_e,
            "op_guia_d": p.op_guia_d, "acabamento_guia": p.acabamento_guia, "tp_acionamento": p.tp_acionamento, "lado_motor": p.lado_motor, "tp_mola": p.tp_mola, "tp_travamento": p.tp_travamento, "posicao_eixo": p.posicao_eixo,
            "tp_instalacao": p.tp_instalacao, "testeira": float(p.testeira or 0), "qtd_pares_trava": float(p.qtd_pares_trava or 0), "pintura_porta": p.pintura_porta, "cor_porta": p.cor_porta, "nr_serie_motor": p.nr_serie_motor,
            "garantia_motor_meses": float(p.garantia_motor_meses or 12), "possui_passagem_pedestre": p.possui_passagem_pedestre, "largura_passagem": p.largura_passagem, "altura_passagem": p.altura_passagem, "obs_porta": p.obs_porta,
            "fotos": [{"id": foto.id, "url": foto.foto.url, "principal": foto.principal, "ordem": foto.ordem} for foto in p.fotos.all().order_by("ordem", "id")],
            "produtos": [{"codProd": pp.produto.codigo, "qtdProd": float(pp.quantidade), "regra_origem": pp.regra_origem, "vl_unit": float(pp.valor_unitario or 0), "vl_total": float(pp.valor_total or 0)}
                for pp in p.produtos.all()
            ],
            "adicionais": [{"codProd": adc.produto.codigo, "qtdProd": float(adc.quantidade), "lado": adc.lado, "regra_origem": adc.regra_origem, "vl_unit": float(adc.valor_unitario or 0), "vl_total": float(adc.valor_total or 0)}
                for adc in p.adicionais.all()
            ],
        })
    return portas_json

@login_required
@transaction.atomic
def clonar_orcamento(request, codigo):
    error_messages = []
    portas_json = []
    form = None
    orcamento = get_object_or_404(Orcamento, codigo=codigo, vinc_emp=request.user.empresa)
    if not request.user.has_perm('orcamentos.clonar_orcamento'):
        messages.info(request, 'Você não tem permissão para clonar orçamentos.')
        return redirect('/orcamentos/lista/')
    try:
        if request.method == 'POST':
            form = OrcamentoForm(data=request.POST, files=request.FILES, empresa=request.user.empresa, user=request.user)
            if not form.is_valid():
                erros = [f"<i class='fa-solid fa-xmark'></i> Campo ({f.label}) é obrigatório!" for f in form if f.errors]
                return render(request, "orcamentos/clonar_orcamento.html", {"form": form, "orcamento": orcamento, "error_messages": erros})
            novo = form.save(commit=False)
            novo.codigo = None
            novo.dt_emi = timezone.now()
            novo.situacao = "Aberto"
            novo.vinc_emp = orcamento.vinc_emp
            novo.save()
            novo.num_orcamento = f"{timezone.now():%Y-}{novo.codigo}"
            novo.save(update_fields=["num_orcamento"])
            # 🔥 Formas de pagamento vêm do que o usuário definiu na tela de clonagem, não das formas do orçamento original
            formas_json = request.POST.get("json_formas_pgto")
            if formas_json:
                try: formas = json.loads(formas_json)
                except json.JSONDecodeError: formas = []
                for f in formas:
                    forma_id = f.get("forma_id")
                    valor = Decimal(str(f.get("valor") or "0"))
                    parcelas = int(f.get("parcelas") or 1)
                    dias = int(f.get("dias") or 0)
                    if not forma_id or valor < Decimal("0.01"): continue
                    try: fp = FormaPgto.objects.get(codigo=forma_id, vinc_emp=request.user.empresa)
                    except FormaPgto.DoesNotExist: continue
                    OrcamentoFormaPgto.objects.create(orcamento=novo, formas_pgto=fp, valor=valor, parcelas=parcelas, dias_intervalo=dias)
            else:
                for forma in orcamento.formas_pgto.all():
                    OrcamentoFormaPgto.objects.create(orcamento=novo, formas_pgto=forma.formas_pgto, valor=forma.valor, parcelas=forma.parcelas, dias_intervalo=forma.dias_intervalo)
            for p in orcamento.portas.all():
                nova_porta = PortaOrcamento.objects.create(orcamento=novo, numero=p.numero, largura=p.largura, altura=p.altura, qtd_lam=p.qtd_lam, m2=p.m2, larg_corte=p.larg_corte, alt_corte=p.alt_corte, rolo=p.rolo,
                    peso=p.peso,fator_peso=p.fator_peso,eixo_motor=p.eixo_motor,tp_lamina=p.tp_lamina,tp_vao=p.tp_vao,op_guia_e=p.op_guia_e,op_guia_d=p.op_guia_d,acabamento_guia=p.acabamento_guia, tp_acionamento=p.tp_acionamento,
                    lado_motor=p.lado_motor,tp_mola=p.tp_mola,tp_travamento=p.tp_travamento,posicao_eixo=p.posicao_eixo,tp_instalacao=p.tp_instalacao,testeira=p.testeira, qtd_pares_trava=p.qtd_pares_trava,pintura_porta=p.pintura_porta,
                    cor_porta=p.cor_porta,nr_serie_motor=p.nr_serie_motor,garantia_motor_meses=p.garantia_motor_meses, possui_passagem_pedestre=p.possui_passagem_pedestre, largura_passagem=p.largura_passagem, altura_passagem=p.altura_passagem, obs_porta=p.obs_porta,
                )
                for pt in p.produtos.all():
                    PortaProduto.objects.create(porta=nova_porta, produto=pt.produto, quantidade=pt.quantidade, valor_unitario=pt.valor_unitario, valor_total=pt.valor_total, regra_origem=pt.regra_origem)
                for ad in p.adicionais.all():
                    PortaAdicional.objects.create(porta=nova_porta,produto=ad.produto,quantidade=ad.quantidade,valor_unitario=ad.valor_unitario,valor_total=ad.valor_total,regra_origem=ad.regra_origem,lado=ad.lado)
            for chave in request.FILES:
                if chave.startswith("fotos_"):
                    numero_porta = int(chave.replace("fotos_", ""))
                    porta = PortaOrcamento.objects.get(orcamento=novo, numero=numero_porta)
                    for foto in request.FILES.getlist(chave):
                        PortaOrcamentoFoto.objects.create(porta=porta, foto=foto)
            # 🔥 só calcula o subtotal DEPOIS de clonar tudo
            novo.atualizar_subtotal()
            if novo.subtotal == 0: raise ValueError("O orçamento precisa ter pelo menos um item com valor.")
            novo.save(update_fields=['subtotal', 'total'])
            registrar_log(request, "CRIAR", "Orçamento", novo.codigo, f"Adicionou o orçamento, Nº: {novo.codigo}, clonando o orçamento Nº: {orcamento.codigo}", novo.id, gerar_alteracoes(obj_novo=novo))
            messages.success(request, "Orçamento clonado com sucesso!")
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url: return redirect(next_url)
            return redirect('/orcamentos/lista/?s=' + str(novo.codigo))
        portas_json = []
        for p in orcamento.portas.all():
            portas_json.append({"numero": p.numero, "largura": float(p.largura), "altura": float(p.altura), "qtd_lam": float(p.qtd_lam or 0), "m2": float(p.m2 or 0), "larg_corte": float(p.larg_corte or 0),
                "alt_corte":float(p.alt_corte or 0),"rolo":float(p.rolo or 0),"peso":float(p.peso or 0),"ft_peso":float(p.fator_peso or 0),"eix_mot":float(p.eixo_motor or 0),"tipo_lamina": p.tp_lamina,
                "tipo_vao":p.tp_vao,"op_guia_e":p.op_guia_e,"op_guia_d":p.op_guia_d,"acabamento_guia":p.acabamento_guia,"tp_acionamento":p.tp_acionamento,"lado_motor":p.lado_motor,"tp_mola":p.tp_mola,
                "tp_travamento":p.tp_travamento,"posicao_eixo":p.posicao_eixo,"tp_instalacao":p.tp_instalacao,"testeira":float(p.testeira or 0),"qtd_pares_trava": float(p.qtd_pares_trava or 0), "pintura_porta": p.pintura_porta,
                "cor_porta":p.cor_porta,"nr_serie_motor":p.nr_serie_motor,"garantia_motor_meses":p.garantia_motor_meses,"possui_passagem_pedestre":p.possui_passagem_pedestre,"largura_passagem":p.largura_passagem,
                "altura_passagem": p.altura_passagem, "obs_porta": p.obs_porta,
                "fotos": [{"id": foto.id, "url": foto.foto.url, "principal": foto.principal, "ordem": foto.ordem,} for foto in p.fotos.all().order_by("ordem", "id")],
                "produtos": [{"codProd":pp.produto.codigo,"qtdProd":float(pp.quantidade),"regra_origem":pp.regra_origem,"vl_unit":float(pp.valor_unitario or 0),"vl_total":float(pp.valor_total or 0),}
                    for pp in p.produtos.all()],
                "adicionais": [{"codProd": adc.produto.codigo,"qtdProd":float(adc.quantidade),"lado":adc.lado,"regra_origem":adc.regra_origem,"vl_unit":float(adc.valor_unitario or 0),"vl_total":float(adc.valor_total or 0),}
                    for adc in p.adicionais.all()]
            })
        form = OrcamentoForm(instance=orcamento, empresa=request.user.empresa, user=request.user)
    except ObjectDoesNotExist: error_messages.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {str(e)}")
    except DatabaseError as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except Exception as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return render(request, "orcamentos/clonar_orcamento.html",{"form": form, "orcamento": orcamento, "error_messages": error_messages, "portas": orcamento.portas.all(), "portas_json": json.dumps(portas_json, default=float), "next": request.GET.get("next", "")})

@login_required
@require_POST
def del_orcamento(request, codigo):
    if not request.user.has_perm('orcamentos.delete_orcamento'):
        messages.info(request, 'Você não tem permissão para deletar orçamentos.')
        return redirect('lista-orcamentos')
    o = get_object_or_404(Orcamento, codigo=codigo, vinc_emp=request.user.empresa)
    if o.situacao in ['Faturado', 'Cancelado']:
        messages.warning(request, 'Orçamentos só podem ser deletados com situação Aberto!')
        return redirect('lista-orcamentos')
    registrar_log(request, "EXCLUIR", "Orçamento", o.codigo, f"Excluiu o orçamento, Nº: {o.codigo}", o.id, gerar_alteracoes(obj_antigo=o))
    o.delete()
    messages.success(request, 'Orçamento deletado com sucesso!')
    return redirect('lista-orcamentos')

@login_required
@transaction.atomic
def faturar_orcamento(request, codigo):
    if not request.user.has_perm('orcamentos.faturar_orcamento'):
        messages.warning(request, 'Você não tem permissão para faturar orçamentos!')
        return redirect('/orcamentos/lista/')
    orcamento = get_object_or_404(Orcamento.objects.select_related('cli', 'vinc_fil', 'vinc_emp').prefetch_related('formas_pgto__formas_pgto', 'portas__produtos__produto', 'portas__adicionais__produto',),
        codigo=codigo, vinc_emp=request.user.empresa)
    if orcamento.situacao == 'Faturado':
        messages.warning(request, f'O orçamento {orcamento.codigo} já foi faturado.')
        return redirect('/orcamentos/lista/')
    formas = list(orcamento.formas_pgto.all())
    if not formas:
        messages.error(request,'Informe ao menos uma forma de pagamento antes de faturar.')
        return redirect(request.META.get('HTTP_REFERER',f'/orcamentos/att/{orcamento.codigo}/'))
    def obter_itens():
        for porta in orcamento.portas.all():
            yield from porta.produtos.all()
            yield from porta.adicionais.all()
    # VALIDAÇÃO DE ESTOQUE
    pode_vender_sem_estoque = request.user.has_perm('orcamentos.vender_sem_estoque_orc')
    if not pode_vender_sem_estoque:
        quantidades = defaultdict(Decimal)
        for item in obter_itens():
            quantidades[item.produto_id] += item.quantidade
        produtos = {produto.id: produto for produto in Produto.objects.filter(id__in=quantidades.keys())}
        erros_estoque = []
        for produto_id, quantidade_necessaria in quantidades.items():
            produto = produtos.get(produto_id)
            if not produto:
                erros_estoque.append(f'Produto ID {produto_id} não encontrado.')
                continue
            if produto.estoque_prod < quantidade_necessaria:
                faltando = quantidade_necessaria - produto.estoque_prod
                erros_estoque.append(f'{produto.desc_prod}: disponível {produto.estoque_prod}, necessário {quantidade_necessaria}, faltam {faltando}')
        if erros_estoque:
            for erro in erros_estoque[:5]:
                messages.error(request, erro)
            if len(erros_estoque) > 5: messages.error(request, f'Existem mais {len(erros_estoque) - 5} produtos com estoque insuficiente.')
            return redirect(request.META.get('HTTP_REFERER', '/orcamentos/lista/'))
    # CONTAS A RECEBER
    for forma in formas:
        gateway = (forma.formas_pgto.gateway or '').strip().lower()
        # Gateway será tratado por integração própria
        if gateway not in ['', 'nenhum', 'none']: continue
        if not forma.formas_pgto.gera_parcelas: continue
        parcelas = forma.parcelas or 1
        valor_parcela = (Decimal(forma.valor) / parcelas).quantize(Decimal('0.01'))
        for i in range(parcelas):
            ContaReceber.objects.create(
                data_emissao=orcamento.dt_emi,vinc_emp=orcamento.vinc_emp,vinc_fil=orcamento.vinc_fil,orcamento=orcamento,cliente=orcamento.cli,forma_pgto=forma.formas_pgto, num_conta=f'O-{orcamento.codigo}',
                valor=valor_parcela, data_vencimento=timezone.now().date() + timedelta(days=forma.dias_intervalo * (i + 1)), situacao='Aberta'
            )
    # BAIXA DE ESTOQUE
    if not pode_vender_sem_estoque:
        for produto_id, quantidade in quantidades.items():
            Produto.objects.filter(codigo=produto_id).update(estoque_prod=F('estoque_prod') - quantidade)
    # FATURAMENTO
    orcamento.situacao = 'Faturado'
    orcamento.dt_fat = timezone.now()
    orcamento.save(update_fields=['situacao', 'dt_fat'])
    tem_avista = any((f.formas_pgto.tipo or "").strip().lower() == "a vista" for f in formas)
    imp_recibo = (orcamento.vinc_fil.imp_recibo_orc or "Não").strip()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        registrar_log(request=request, tipo="FATURAR", modulo="Orçamento", objeto=orcamento.codigo, objeto_id=orcamento.id, descricao=f"Faturou o orçamento nº {orcamento.codigo}",
            alteracoes={"Valor Total":orcamento.total,"Cliente":str(orcamento.cli),"Técnico":str(orcamento.solicitante),"Forma de Pagamento":", ".join(str(fp.formas_pgto) for fp in orcamento.formas_pgto.all())}
        )
        return JsonResponse({"success": True, "codigo": orcamento.codigo, "tem_avista": tem_avista, "imp_recibo": imp_recibo, "url_recibo": reverse("recibo_orcamento", args=[orcamento.codigo]),
            "redirect": f"/orcamentos/lista/?s={orcamento.codigo}",
        })
    registrar_log(request=request, tipo="FATURAR", modulo="Orçamento", objeto=orcamento.codigo, objeto_id=orcamento.id, descricao=f"Faturou o orçamento nº {orcamento.codigo}",
        alteracoes={"Valor Total":orcamento.total,"Cliente":str(orcamento.cli),"Técnico":str(orcamento.solicitante),"Forma de Pagamento":", ".join(str(fp.formas_pgto) for fp in orcamento.formas_pgto.all())}
    )
    messages.success(request, f"Orçamento {orcamento.codigo} faturado com sucesso.")
    return redirect(f"/orcamentos/lista/?s={orcamento.codigo}")

@login_required
def gerar_pagamento_orcamento(request, orcamento_id):
    orcamento = get_object_or_404(Orcamento, codigo=orcamento_id, vinc_emp=request.user.empresa)
    from django.contrib.contenttypes.models import ContentType
    ct = ContentType.objects.get_for_model(orcamento)
    if Pagamento.objects.filter(content_type=ct, object_id=orcamento.codigo).exists(): return JsonResponse({"erro": "Pagamento já gerado."}, status=400)
    pagamentos = gerar_pagamentos_orcamento(orcamento)
    if not pagamentos: return JsonResponse({"erro": "Nenhum pagamento gerado."}, status=400)
    return JsonResponse({"pagamentos": pagamentos})

@login_required
def status_pagamento_orcamento(request, orcamento_id):
    orcamento = get_object_or_404(Orcamento, codigo=orcamento_id, vinc_emp=request.user.empresa)
    ct = ContentType.objects.get_for_model(orcamento)
    pagamentos = Pagamento.objects.filter(content_type=ct, object_id=orcamento.codigo)
    data = [{"txid": p.txid, "status": p.status, "valor": str(p.valor)} for p in pagamentos]
    return JsonResponse({"pagamentos": data})

@require_POST
@login_required
@transaction.atomic
def cancelar_orcamento(request, codigo):
    orcamento = get_object_or_404(Orcamento.objects.prefetch_related('portas__produtos__produto','portas__adicionais__produto'), codigo=codigo, vinc_emp=request.user.empresa)
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
            return redirect('/orcamentos/lista/?s=' + str(orcamento.codigo))
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
        orcamento.motivo = motivo
        registrar_log(request=request, tipo="CANCELAR", modulo="Orçamento", objeto=orcamento.codigo, objeto_id=orcamento.id, descricao=f"Cancelou o orçamento nº {orcamento.codigo}",
            alteracoes={"Motivo": orcamento.motivo, "Data do Cancelamento": orcamento.dt_fat,}
        )
        orcamento.save(update_fields=['situacao', 'dt_fat'])
        messages.success(request, f'Orçamento {orcamento.codigo} cancelado com sucesso!')
        return redirect('/orcamentos/lista/?s=' + str(orcamento.codigo))

@login_required
@require_POST
def alterar_status_orcamento(request):
    try:
        orc_id = request.POST.get("id")
        novo_status = request.POST.get("status")
        if not orc_id or not novo_status: return JsonResponse({"status": "erro", "mensagem": "Dados inválidos"}, status=400)
        orc = get_object_or_404(Orcamento, codigo=orc_id, vinc_emp=request.user.empresa)
        it_old = Orcamento.objects.get(codigo=orc.codigo, vinc_emp=request.user.empresa)
        orc.status = novo_status
        orc.save(update_fields=["status"])
        registrar_log(request, "ALTERAR", "Orçamento", orc.codigo, f"Alterou o status da operação da(s) Porta(s) de Enrolar do Orçamento: {orc.codigo}", orc.id, gerar_alteracoes(it_old, orc))
        return JsonResponse({"status": "ok","mensagem": "Status atualizado com sucesso!"})
    except Exception as e: return JsonResponse({"status": "erro","mensagem": str(e)}, status=500)

@login_required
def imprimir_comprovante(request, codigo):
    orcamento = get_object_or_404(Orcamento, codigo=codigo, vinc_emp=request.user.empresa)
    formas_pgto = orcamento.formas_pgto.all()
    # Criando uma lista de formas convertidas para uso no template
    orcamento.formas_convertidas = [{"id": f.codigo, "descricao": f.formas_pgto.descricao if hasattr(f, 'formas_pgto') else str(f), "valor": float(f.valor)} for f in formas_pgto]
    return render(request, 'orcamentos/comprovante.html', {'orcamento': orcamento, 'formas_pgto': formas_pgto,})

segoe_ui_bold = os.path.join(settings.BASE_DIR, "static", "fonts", "segoe-ui-bold.ttf")
segoe_ui = os.path.join(settings.BASE_DIR, "static", "fonts", "Segoe UI.ttf")
arial_narrow_bold = os.path.join(settings.BASE_DIR, "static", "fonts", "arialnarrow_bold.ttf")
times = os.path.join(settings.BASE_DIR, "static", "fonts", "Times.ttf")
times_bold = os.path.join(settings.BASE_DIR, "static", "fonts", "Times_Bold.ttf")
times_bold_italic = os.path.join(settings.BASE_DIR, "static", "fonts", "Times-Bold-Italic.ttf")

@login_required
def imprimir_comp_a4(request, codigo):
    orcamento = get_object_or_404(Orcamento, codigo=codigo, vinc_emp=request.user.empresa)
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    larg_pag, alt_pag = A4
    pdfmetrics.registerFont(TTFont('Times', times))
    pdfmetrics.registerFont(TTFont('Times Bold', times_bold))
    c.setTitle(f'RESUMO ORÇAMENTO - {orcamento.codigo}')
    c.setFont("Times", 10)
    logo_path = os.path.join(settings.MEDIA_ROOT, str(orcamento.vinc_fil.logo))
    if os.path.exists(logo_path):
        with Image.open(logo_path) as img:
            if img.mode in ('RGBA', 'LA'):
                background = Image.new("RGB", img.size, (255, 255, 255))  # branco
                background.paste(img, mask=img.split()[3])  # usar alpha como máscara
                img = background
            else: img = img.convert("RGB")
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
    c.drawCentredString(larg_pag/2, y, f"Resumo Orçamento {orcamento.codigo} ({orcamento.situacao})")
    y -= 8
    c.line(40, y, larg_pag-40, y)
    y -= 20
    col_1 = [("Nº Orçamento:", orcamento.codigo), ("Dt. Emissão:", orcamento.dt_emi.strftime("%d/%m/%Y")), ("Solicitante:", orcamento.nome_solicitante), ("Razão Social:", orcamento.cli.razao_social),
        ("Cliente:", f"{orcamento.cli.codigo} - {orcamento.nome_cli}"), ("Endereço:", f"{orcamento.cli.endereco}, Nº {orcamento.cli.numero}"), ("CPF/CNPJ:", orcamento.cli.cpf_cnpj),]
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
    response['Content-Disposition'] = f'filename="RESUMO ORÇAMENTO - {orcamento.codigo}.pdf"'
    return response

@login_required
def pdf_contrato_html(request, codigo):
    o = Orcamento.objects.prefetch_related('portas__produtos__produto', 'portas__adicionais__produto').get(codigo=codigo, vinc_emp=request.user.empresa)
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
            else: img = img.convert("RGB")
            buffer = BytesIO()
            img.save(buffer, format="JPEG")
            logo_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    html_string = render_to_string('orcamentos/pdf_contrato.html', {'o': o, 'portas': portas, 'linhas_formas': linhas_formas, 'logo_base64': logo_base64})
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = (f'inline; filename="CONTRATO ORÇAMENTO PORTA ENROLAR - {o.codigo}.pdf"')
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
def pdf_proposta_html(request, codigo):
    o = Orcamento.objects.get(codigo=codigo, vinc_emp=request.user.empresa)
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
    response["Content-Disposition"] = ( f'inline; filename="PROPOSTA COMERCIAL - {o.codigo}.pdf"' )
    return response

@login_required
def pdf_orcamento_html(request, codigo):
    o = Orcamento.objects.prefetch_related(Prefetch('portas__produtos', queryset=PortaProduto.objects.select_related('produto').order_by('produto__desc_prod')), Prefetch('portas__adicionais',queryset=PortaAdicional.objects.select_related('produto').order_by('produto__desc_prod'))).get(codigo=codigo, vinc_emp=request.user.empresa)
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
                else: img = img.convert("RGB")
                buffer = BytesIO()
                img.save(buffer, format="JPEG")
                logo_base64 = base64.b64encode(buffer.getvalue()).decode()
    html = render_to_string('orcamentos/pdf_orcamento.html', {'o': o, 'portas': portas, 'linhas_formas': linhas_formas, 'logo_base64': logo_base64}, request=request)
    pdf = HTML(string=html, base_url=request.build_absolute_uri('/') ).write_pdf( stylesheets=[CSS(string=""" @page {size: A4; margin: 25mm 15mm 20mm 15mm;} body {font-family: Arial, sans-serif; font-size: 11px;} """)])
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = (f'inline; filename="ORÇAMENTO PORTA ENROLAR - {o.codigo}.pdf"')
    return response

@login_required
def pdf_producao_html(request, codigo):
    o = get_object_or_404(
        Orcamento.objects.select_related('vinc_fil','cli','solicitante',).prefetch_related(Prefetch('portas__produtos', queryset=PortaProduto.objects.select_related('produto').order_by('produto__desc_prod')),
            Prefetch('portas__adicionais',queryset=PortaAdicional.objects.select_related('produto').exclude(produto__especifico='Serviço/Transporte').order_by('produto__desc_prod')), 'portas',), codigo=codigo, vinc_emp=request.user.empresa)
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
                else: img = img.convert("RGB")
                buffer = BytesIO()
                img.save(buffer, format="JPEG")
                logo_base64 = base64.b64encode(buffer.getvalue()).decode()
    context = {'o': o, 'portas': portas, 'logo_base64': logo_base64,}
    if o.vinc_fil.layout_prod == "1": html = render_to_string('orcamentos/pdf_producao.html', context, request=request)
    else: html = render_to_string('orcamentos/pdf_producao_v2.html', context, request=request)
    pdf = HTML(string=html, base_url=request.build_absolute_uri('/')).write_pdf(
        stylesheets=[CSS(string="""
                @page {size: A4; margin: 12mm 10mm 12mm 10mm;
                }
                body {font-family: Arial, Helvetica, sans-serif; font-size: 11px; color: #111;}""")])
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = (f'inline; filename="ORDEM DE PRODUCAO PORTA ENROLAR - {o.codigo}.pdf"')
    return response

@login_required
def recibo_orcamento(request, codigo):
    orcamento = get_object_or_404(Orcamento.objects.select_related("cli", "vinc_emp", "vinc_fil").prefetch_related("formas_pgto__formas_pgto"), codigo=codigo, vinc_emp=request.user.empresa)
    logo_base64 = None
    if orcamento.vinc_fil and orcamento.vinc_fil.logo:
        logo_path = os.path.join(settings.MEDIA_ROOT, str(orcamento.vinc_fil.logo))
        if os.path.exists(logo_path):
            with Image.open(logo_path) as img:
                if img.mode in ('RGBA', 'LA'):
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[-1])
                    img = bg
                else: img = img.convert("RGB")
                buffer = BytesIO()
                img.save(buffer, format="JPEG")
                logo_base64 = base64.b64encode(buffer.getvalue()).decode()
    total = Decimal("0.00")
    descricao = []
    for forma in orcamento.formas_pgto.all():
        if forma.formas_pgto.tipo == "A vista":
            total += forma.valor
        descricao.append(f"{forma.formas_pgto.descricao} - R$ {forma.valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    html = render_to_string("orcamentos/recibo.html", {"orcamento": orcamento, "cliente": orcamento.cli, "filial": orcamento.vinc_fil, "total": total, "formas": descricao, "logo_base64": logo_base64}, request=request)
    pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="recibo_{orcamento.codigo}.pdf"'
    return response