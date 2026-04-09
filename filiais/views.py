from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from .models import Filial
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from datetime import datetime, time
from calendar import monthrange
import unicodedata
from django.core.paginator import Paginator
from .forms import FilialForm, FilialReadOnlyForm, EmpresaLoginForm
from util.permissoes import verifica_permissao
from django.http import JsonResponse
from orcamentos.models import Orcamento
from contas.forms import SuperuserLoginForm
from notifications.models import Notification
from estados.models import Estado
from cidades.models import Cidade
from bairros.models import Bairro
from collections import defaultdict

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

def login_superusuario(request):
    if request.method == "POST":
        form = SuperuserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_superuser:
                login(request, user)
                return redirect("/empresas/lista/")
            else:
                messages.error(request, "Apenas superusuários podem acessar por aqui.")
        else:
            messages.error(request, "Usuário ou senha incorretos.")
    else:
        form = SuperuserLoginForm()

    return render(request, 'registration/login_superuser.html', {'form': form})

def login_filial(request):
    if request.method == "POST":
        form = EmpresaLoginForm(request.POST)
        form.request = request  # importante pro authenticate

        if form.is_valid():
            login(request, form.cleaned_data['user'])
            return redirect("inicio")
        else:
            # 🔥 AQUI É O PULO DO GATO
            for field, errors in form.errors.items():
                for error in form.non_field_errors():
                    messages.error(request, error)

    else:
        form = EmpresaLoginForm()

    return render(request, "registration/login.html", {"form": form})

def verificar_ou_criar_localizacao(request):
    estado_nome = request.GET.get('estado')
    cidade_nome = request.GET.get('cidade')
    bairro_nome = request.GET.get('bairro')
    if not estado_nome or not cidade_nome:
        return JsonResponse({'erro': 'Estado e cidade são obrigatórios.'}, status=400)
    # Normalização
    estado_nome = estado_nome.strip().upper()
    cidade_nome = cidade_nome.strip().upper()
    bairro_nome = bairro_nome.strip().upper() if bairro_nome else None
    # Estado
    estado = Estado.objects.filter(nome_estado__iexact=estado_nome, vinc_emp=request.user.empresa).first()
    if not estado:
        estado = Estado.objects.create(nome_estado=estado_nome, vinc_emp=request.user.empresa)
    # Cidade
    cidade = Cidade.objects.filter(nome_cidade__iexact=cidade_nome, vinc_emp=request.user.empresa).first()
    if not cidade:
        cidade = Cidade.objects.create(nome_cidade=cidade_nome, vinc_emp=request.user.empresa)
    # Bairro
    bairro = None
    if bairro_nome:
        bairro = Bairro.objects.filter(nome_bairro__iexact=bairro_nome, vinc_emp=request.user.empresa).first()
        if not bairro:
            bairro = Bairro.objects.create(nome_bairro=bairro_nome, vinc_emp=request.user.empresa)
    response = {
        'estado_id': estado.id, 'estado_nome': estado.nome_estado, 'cidade_id': cidade.id, 'cidade_nome': cidade.nome_cidade, 'bairro_id': bairro.id if bairro else "", 'bairro_nome': bairro.nome_bairro if bairro else "",
    }
    return JsonResponse(response)

@login_required
def verificar_parcelas(request):
    parcelas = int(request.GET.get('parcelas', 0))
    filial = request.user.filial_user
    if parcelas > filial.max_parcelas:
        return JsonResponse({'permitido': False, 'maximo': filial.max_parcelas})
    return JsonResponse({'permitido': True})

@login_required
def notificacoes_ajax(request):
    notificacoes = Notification.objects.filter(recipient=request.user, unread=True)
    data = []
    for n in notificacoes:
        data.append({'id': n.id, 'verb': n.verb, 'description': n.description, 'solicitacao_id': n.data.get('solicitacao_id') if n.data else None,})
    return JsonResponse({'notificacoes': data})

@verifica_permissao('filiais.view_filial')
@login_required
def lista_filiais(request):
    s = request.GET.get('s')               # texto de busca
    tp = request.GET.get('tp')             # tipo de busca (desc ou cod)
    f_s = request.GET.get('sit')           # situação: Ativa / Inativa
    t_pes = request.GET.get('t_pes')       # tipo pessoa: Física / Jurídica
    dt_ini = request.GET.get('dt_ini')     # data inicial
    dt_fim = request.GET.get('dt_fim')     # data final
    p_dt = request.GET.get('p_dt')         # filtrar por data? Sim / Não
    reg = request.GET.get('reg', '10')     # registros por página
    empresa = request.user.empresa
    filiais = Filial.objects.filter(vinc_emp=empresa)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        filiais = filiais.filter(fantasia_normalizado__icontains=norm_s).order_by('fantasia')
    elif tp == 'cod' and s:
        try:
            filiais = filiais.filter(id__iexact=s).order_by('fantasia')
        except ValueError:
            filiais = Filial.objects.none()
    if p_dt == 'Sim' and dt_ini and dt_fim:
        try:
            # Converter as datas de entrada de string para date
            dt_ini_dt = datetime.strptime(dt_ini, '%d/%m/%Y').date()
            dt_fim_dt = datetime.strptime(dt_fim, '%d/%m/%Y').date()

            # if list_p == 'dt_criacao':
            filiais = filiais.filter(dt_criacao__range=(dt_ini_dt, dt_fim_dt))
            # elif list_p == 'dt_inativacao':
            #     filiais = filiais.filter(dt_inativacao__range=(dt_ini_dt, dt_fim_dt))
        except ValueError:
            filiais = Filial.objects.none()
    # Filtro por situação (ativa/inativa)
    if f_s in ['Ativa', 'Inativa']:
        filiais = filiais.filter(situacao=f_s)
    # Filtro por tipo de pessoa (física/jurídica) - caso use esse campo na model
    if t_pes in ['Física', 'Jurídica']:
        filiais = filiais.filter(pessoa=t_pes)
    # Paginação
    if reg == 'todos':
        num_pagina = filiais.count() or 1
    else:
        try:
            num_pagina = int(reg)
        except ValueError:
            num_pagina = 10
    paginator = Paginator(filiais, num_pagina)
    page = request.GET.get('page')
    filiais = paginator.get_page(page)
    return render(request, 'filiais/lista.html', {'filiais': filiais, 's': s, 'tp': tp, 't_pes': t_pes, 'dt_ini': dt_ini, 'dt_fim': dt_fim, 'p_dt': p_dt, 'reg': reg})

from django.db import models
@login_required
def filiais_vinculadas_ajax(request):
    termo_busca = request.GET.get('term', '')
    empresa = request.user.empresa
    filial_principal = empresa
    if filial_principal is None:
        return JsonResponse({'results': []})
    filiais = Filial.objects.filter(
        models.Q(vinculada_a=filial_principal) | models.Q(id=filial_principal.id),
        situacao='Ativa',
        fantasia__icontains=termo_busca
    ).values('id', 'fantasia')
    results = [{'id': f['id'], 'text': f['fantasia'].upper()} for f in filiais]
    return JsonResponse({'results': results})

@login_required
def lista_filiais_ajax(request):
    term = request.GET.get('term', '')
    empresa = request.user.empresa
    filiais = Filial.objects.filter(vinc_emp=empresa, situacao='Ativa', fantasia__icontains=term)
    data = {'filiais': [{'id': filial.id, 'fantasia': filial.fantasia.upper()} for filial in filiais]}
    return JsonResponse(data)

@login_required
def dados_filiais_js(request):
    empresa = request.user.empresa
    if not empresa:
        return JsonResponse({}, status=403)
    filiais = Filial.objects.filter(
        vinc_emp=empresa,
        situacao='Ativa'
    ).values('id', 'cli_id', 'tec_id')
    data = {
        str(f['id']): {
            'cli': f['cli_id'],
            'tec': f['tec_id'],
        }
        for f in filiais
    }
    return JsonResponse(data)

@login_required
def add_filial(request):
    if not request.user.has_perm('filiais.add_filial'):
        messages.info(request, 'Você não tem permissão para adicionar filiais.')
        return redirect('/filiais/lista/')
    try:
        empresa = request.user.empresa
        filial_atual = Filial.objects.get(vinc_emp=empresa, principal=True)
    except Filial.DoesNotExist:
        messages.error(request, 'Filial principal não encontrada para este usuário.')
        return redirect('/filiais/lista/')
    # 🔹 Filial principal
    filial_principal = filial_atual
    qtd_permitida = empresa.qtd_filial
    total_filiais_vinculadas = 1 + filial_principal.filiais_secundarias.filter(vinc_emp=empresa, situacao='Ativa').count()
    if total_filiais_vinculadas >= qtd_permitida:
        messages.warning(request, f'Limite de {qtd_permitida} filial(is) ativa(s) atingido para sua empresa.')
        return redirect('/filiais/lista/')
    if request.method == 'POST':
        form = FilialForm(request.POST, request.FILES, empresa=request.user.empresa)
        if form.is_valid():
            nova_filial = form.save(commit=False)
            nova_filial.vinc_emp = empresa
            nova_filial.vinculada_a = filial_principal
            nova_filial.principal = False
            nova_filial.situacao = 'Ativa'
            nova_filial.save()
            messages.success(request, 'Filial cadastrada com sucesso.')
            return redirect('/filiais/lista/')
    else:
        form = FilialForm(empresa=request.user.empresa)
    return render(request, 'filiais/add_filial.html', {'form': form})

@login_required
def att_filial(request, id):
    filial = get_object_or_404(Filial, pk=id, vinc_emp=request.user.empresa)
    form = FilialForm(instance=filial, empresa=request.user.empresa)
    if not request.user.has_perm('filiais.change_filial'):
        messages.info(request, 'Você não tem permissão para editar filiais.')
        return redirect('/filiais/lista/')
    if request.method == 'POST':
        form = FilialForm(request.POST, request.FILES, instance=filial, empresa=request.user.empresa)
        if form.is_valid():
            form.save()
            next_url = request.POST.get('next') or request.GET.get('next')
            messages.success(request, 'Filial atualizada com sucesso.')
            if next_url:
                return redirect(next_url)
            else:
                return redirect('/filiais/lista/?tp=cod&s={filial.id}')
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'filiais/att_filial.html', {'form': form, 'filial': filial, 'error_messages': error_messages})
    else:
        form = FilialForm(instance=filial, empresa=request.user.empresa)

    return render(request, 'filiais/att_filial.html', {'form': form, 'filial': filial})

@login_required
def del_filial(request, id):
    filial = get_object_or_404(Filial, pk=id, vinc_emp=request.user.empresa)
    if not request.user.has_perm('filiais.delete_filial'):
        messages.info(request, 'Você não tem permissão para deletar filiais.')
        return redirect('/filiais/lista/')
    if filial.vinculada_a != request.user.usuario.filial:
        messages.error(request, 'Você não tem permissão para deletar esta filial.')
        return redirect('/filiais/lista/')
    if request.method == 'POST':
        filial.delete()
        messages.success(request, 'Filial excluída com sucesso.')
        return redirect('/filiais/lista/')
    form = FilialReadOnlyForm(instance=filial, empresa=request.user.empresa)
    return render(request, 'filiais/del_filial.html', {'filial': filial, 'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('/accounts/login')

@login_required
def logout_view_superuser(request):
    logout(request)
    return redirect('/accounts/login-superuser')


@login_required
def dashboard(request):
    if request.user.is_superuser:
        return redirect('/empresas/lista/')
    dt_ini = request.GET.get('dt_ini')
    dt_fim = request.GET.get('dt_fim')
    data_atual = datetime.today()
    # Período padrão: mês atual
    primeiro_dia_mes = data_atual.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ultimo_dia_mes = data_atual.replace(day=monthrange(data_atual.year, data_atual.month)[1], hour=23, minute=59, second=59, microsecond=999999)
    data_inicial = None
    data_final = None
    try:
        if dt_ini and dt_fim:
            data_inicial = datetime.strptime(dt_ini, '%d/%m/%Y').date()
            data_final = datetime.strptime(dt_fim, '%d/%m/%Y').date()
            dt_ini_dt = datetime.combine(data_inicial, time.min)
            dt_fim_dt = datetime.combine(data_final, time.max)
        else:
            dt_ini_dt = primeiro_dia_mes
            dt_fim_dt = ultimo_dia_mes
    except ValueError:
        dt_ini_dt = primeiro_dia_mes
        dt_fim_dt = ultimo_dia_mes
        dt_ini = ''
        dt_fim = ''
        data_inicial = None
        data_final = None
    orcamentos_no_intervalo = Orcamento.objects.filter(dt_emi__range=(dt_ini_dt, dt_fim_dt), vinc_emp=request.user.empresa).order_by('dt_emi')
    orcamentos_abertos = orcamentos_no_intervalo.filter(situacao='Aberto').count()
    orcamentos_faturados = orcamentos_no_intervalo.filter(situacao='Faturado').count()
    orcamentos_cancelados = orcamentos_no_intervalo.filter(situacao='Cancelado').count()
    tot_orc_ab = 0.0
    tot_orc_fat = 0.0
    tot_orc_canc = 0.0
    media_valor_fat = 0.0
    for orcamento in orcamentos_no_intervalo:
        formas = orcamento.formas_pgto.all()
        total_valor = sum(float(f.valor) for f in formas)
        if orcamento.situacao == 'Aberto':
            tot_orc_ab += total_valor
        elif orcamento.situacao == 'Faturado':
            tot_orc_fat += total_valor
        elif orcamento.situacao == 'Cancelado':
            tot_orc_canc += total_valor
    if orcamentos_faturados > 0:
        media_valor_fat = tot_orc_fat / orcamentos_faturados
    dados_tecnicos = defaultdict(lambda: {'nome': '', 'qtd': 0, 'total': 0.0})
    orcamentos_faturados_qs = Orcamento.objects.filter(dt_emi__range=(dt_ini_dt, dt_fim_dt), vinc_emp=request.user.empresa, situacao='Faturado')
    for orc in orcamentos_faturados_qs:
        tecnico_id = orc.solicitante.id if orc.solicitante else None
        tecnico_nome = orc.solicitante.nome if orc.solicitante else 'Não definido'
        if tecnico_id is not None:
            dados_tecnicos[tecnico_id]['nome'] = tecnico_nome
            dados_tecnicos[tecnico_id]['qtd'] += 1
            valor_total = sum(float(f.valor) for f in orc.formas_pgto.all())
            dados_tecnicos[tecnico_id]['total'] += valor_total
    orcamentos_por_tecnico = sorted(
        [
            {'id': k, 'nome': v['nome'], 'qtd': v['qtd'], 'total': v['total']}
            for k, v in dados_tecnicos.items()
        ],
        key=lambda x: -x['qtd']
    )
    context = {
        'orcamentos_no_intervalo': orcamentos_no_intervalo, 'orcamentos_faturados': orcamentos_faturados, 'orcamentos_abertos': orcamentos_abertos, 'orcamentos_cancelados': orcamentos_cancelados,
        'primeiro_dia_mes': primeiro_dia_mes, 'ultimo_dia_mes': ultimo_dia_mes, 'total_abertos': tot_orc_ab, 'total_faturados': tot_orc_fat, 'total_cancelados': tot_orc_canc, 'media_valor_fat': media_valor_fat,
        'tecnicos': orcamentos_por_tecnico, 'data_atual': data_atual, 'dt_ini': dt_ini, 'dt_fim': dt_fim, 'data_inicial': data_inicial, 'data_final': data_final,
    }
    return render(request, 'dashbord.html', context)