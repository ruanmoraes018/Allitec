from django.shortcuts import render, redirect, get_object_or_404
from tecnicos.models import Tecnico
from .models import Empresa
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from datetime import datetime
import unicodedata
from django.core.paginator import Paginator
from .forms import EmpresaForm
from util.permissoes import verifica_permissao
from filiais.models import Filial, Usuario
from clientes.models import Cliente
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado
from django.http import JsonResponse
from django.db.models import Q
from django.db import transaction
from empresas.services import EmpresaService

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('empresas.view_empresa')
@login_required
def lista_empresas(request):
    s = request.GET.get('s')               # texto de busca
    tp = request.GET.get('tp')             # tipo de busca (desc ou cod)
    f_s = request.GET.get('sit')           # situação: Ativa / Inativa
    t_pes = request.GET.get('t_pes')       # tipo pessoa: Física / Jurídica
    dt_ini = request.GET.get('dt_ini')     # data inicial
    dt_fim = request.GET.get('dt_fim')     # data final
    p_dt = request.GET.get('p_dt')         # filtrar por data? Sim / Não
    reg = request.GET.get('reg', '10')     # registros por página
    dia_venc = request.GET.get('dia_venc')
    empresas = Empresa.objects.all().order_by('fantasia')
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        empresas = empresas.filter(fantasia_normalizado__icontains=norm_s).order_by('fantasia')
    elif tp == 'cod' and s:
        try:
            empresas = empresas.filter(id__icontains=s).order_by('fantasia')
        except ValueError:
            empresas = Empresa.objects.none()
    if dia_venc in ['05', '10', '15', '20', '25', '30']:
        empresas = empresas.filter(dia_venc=dia_venc)
    if p_dt == 'Sim' and dt_ini and dt_fim:
        try:
            dt_ini_dt = datetime.strptime(dt_ini, '%d/%m/%Y').date()
            dt_fim_dt = datetime.strptime(dt_fim, '%d/%m/%Y').date()
            empresas = empresas.filter(dt_criacao__range=(dt_ini_dt, dt_fim_dt))
        except ValueError:
            empresas = Empresa.objects.none()
    if f_s in ['Ativa', 'Inativa']:
        empresas = empresas.filter(situacao=f_s)
    if t_pes in ['Física', 'Jurídica']:
        empresas = empresas.filter(pessoa=t_pes)
    if reg == 'todos':
        num_pagina = empresas.count() or 1
    else:
        try:
            num_pagina = int(reg)
        except ValueError:
            num_pagina = 10
    paginator = Paginator(empresas, num_pagina)
    page = request.GET.get('page')
    empresas = paginator.get_page(page)
    return render(request, 'empresas/lista.html', {
        'empresas': empresas, 's': s, 'tp': tp, 't_pes': t_pes, 'dt_ini': dt_ini, 'dt_fim': dt_fim, 'p_dt': p_dt, 'dia_venc': dia_venc, 'reg': reg
    })

@login_required
def lista_empresas_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    try:
        filtros = Q(situacao__iexact='Ativa')
        if termo_busca.isdigit():
            condicao_busca = Q(fantasia__icontains=termo_busca) | Q(id=termo_busca)
        else:
            condicao_busca = Q(fantasia__icontains=termo_busca)
        empresas = Empresa.objects.filter(filtros & condicao_busca)[:20]
        results = [{'id': emp.id, 'text': f"{emp.id} - {emp.fantasia.upper()}"} for emp in empresas]
        return JsonResponse({'results': results})
    except Exception as e:
        print(f"Erro na busca AJAX: {e}")
        return JsonResponse({'results': [], 'error': str(e)})

@login_required
def add_empresa(request):
    if not request.user.has_perm('empresas.add_empresa'):
        messages.info(request, 'Você não tem permissão para adicionar empresas.')
        return redirect('/empresas/lista/')
    if request.method == 'POST':
        form = EmpresaForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                EmpresaService.criar_empresa_com_estrutura(
                    form=form,
                    request_files=request.FILES
                )
                messages.success(request, 'Empresa cadastrada com sucesso.')
                return redirect('/empresas/lista/')
            except Exception as e:
                messages.error(request, f'Erro ao cadastrar empresa: {str(e)}')
        error_messages = [
            f"<i class='fa-solid fa-xmark'></i> Campo ({f.label}) é obrigatório!"
            for f in form if f.errors
        ]
        return render(request, 'empresas/add.html', {
            'form': form,
            'error_messages': error_messages
        })
    return render(request, 'empresas/add.html', {
        'form': EmpresaForm()
    })

@login_required
def att_empresa(request, id):
    empresa = get_object_or_404(Empresa, id=id)
    form = EmpresaForm(instance=empresa)
    if not request.user.has_perm('empresas.change_empresa'):
        messages.info(request, 'Você não tem permissão para editar empresas.')
        return redirect('/empresas/lista/')
    if request.method == 'POST':
        form = EmpresaForm(request.POST, request.FILES, instance=empresa)
        if form.is_valid():
            form.save()
            next_url = request.POST.get('next') or request.GET.get('next')
            messages.success(request, 'Empresa atualizada com sucesso.')
            if next_url:
                return redirect(next_url)
            else:
                return redirect('/empresas/lista/')
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'empresas/att.html', {'form': form, 'empresa': empresa, 'error_messages': error_messages})
    else:
        form = EmpresaForm(instance=empresa)

    return render(request, 'empresas/att.html', {'form': form, 'empresa': empresa})

@login_required
def del_empresa(request, id):
    empresa = get_object_or_404(Empresa, id=id)

    if not request.user.has_perm('empresas.delete_empresa'):
        messages.info(request, 'Você não tem permissão para deletar empresas.')
        return redirect('/empresas/lista/')

    if request.method == 'POST':
        empresa.delete()
        messages.success(request, 'Empresa excluída com sucesso.')
        return redirect('/empresas/lista/')
    return render(request, 'empresas/del_empresa.html')
