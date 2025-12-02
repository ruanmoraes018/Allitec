from datetime import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Tecnico
from .forms import TecnicoForm
import unicodedata
from django.http import JsonResponse
from filiais.models import Usuario
import json
from django.http import HttpResponse
import os
from django.conf import settings
from util.permissoes import verifica_permissao
import ast
from django.db.models.functions import Concat, Substr
from django.db.models import Q

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('tecnicos.view_tecnico')
@login_required
def lista_tecnicos(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    f_s = request.GET.get('sit')
    dt_ini = request.GET.get('dt_ini')
    dt_fim = request.GET.get('dt_fim')
    p_dt = request.GET.get('p_dt')
    reg = request.GET.get('reg', '10')

    tecnicos = Tecnico.objects.filter(vinc_emp=request.user.empresa)

    if tp == 'nome' and s:
        norm_s = remove_accents(s).lower()
        tecnicos = tecnicos.filter(nome__icontains=norm_s).order_by('nome')
    elif tp == 'cod' and s:
        try:
            tecnicos = tecnicos.filter(id__iexact=s).order_by('nome')
        except ValueError:
            tecnicos = Tecnico.objects.none()

    tecnicos = tecnicos.annotate(
        dt_reg_sortable=Concat(Substr('dt_reg', 7, 4), Substr('dt_reg', 4, 2), Substr('dt_reg', 1, 2))
    )

    if p_dt == 'Sim' and dt_ini and dt_fim:
        try:
            dt_ini_dt = datetime.strptime(dt_ini, '%d/%m/%Y')
            dt_fim_dt = datetime.strptime(dt_fim, '%d/%m/%Y')
            dt_ini_sort = dt_ini_dt.strftime('%Y%m%d')
            dt_fim_sort = dt_fim_dt.strftime('%Y%m%d')
            tecnicos = tecnicos.filter(dt_reg_sortable__gte=dt_ini_sort, dt_reg_sortable__lte=dt_fim_sort)
        except ValueError:
            tecnicos = Tecnico.objects.none()

    if f_s in ['Ativo', 'Inativo']:
        tecnicos = tecnicos.filter(situacao=f_s).order_by('nome')
    if reg == 'todos':
            num_pagina = tecnicos.count() or 1  # Mostra todas as filials
    else:
        try:
            num_pagina = int(reg)
        except ValueError:
            num_pagina = 10

    paginator = Paginator(tecnicos, num_pagina)
    page = request.GET.get('page')
    tecnicos = paginator.get_page(page)

    return render(request, 'tecnicos/lista.html', {
        'tecnicos': tecnicos,
        's': s,
        'tp': tp,
        'dt_ini': dt_ini,
        'dt_fim': dt_fim,
        'p_dt': p_dt,
        'reg': reg,
    })

@login_required
def lista_tecnicos_ajax(request):
    term = request.GET.get('term', '').strip()  # Captura o termo digitado
    tecnicos = Tecnico.objects.filter(
        Q(id__icontains=term) | Q(nome__icontains=term)  # Busca por ID ou fantasia
    )[:10]  # Limita a 10 resultados

    tecnicos_data = [
        {
            'id': tecnico.id,
            'nome': tecnico.nome
        }
        for tecnico in tecnicos
    ]
    return JsonResponse({'tecnicos': tecnicos_data})

@login_required
def add_tecnico(request):
    if not request.user.has_perm('tecnicos.add_tecnico'):
        messages.info(request, 'Você não tem permissão para adicionar técnicos.')
        return redirect('/tecnicos/lista/')
    if request.method == 'POST':
        form = TecnicoForm(request.POST)
        if form.is_valid():
            t = form.save(commit=False)
            if request.user.is_authenticated:
                try:
                    t.vinc_emp = request.user.empresa  # Busca a filial do usuário logado
                except Usuario.DoesNotExist:
                    return JsonResponse({'error': 'Usuário não possui filial vinculada'}, status=400)
            t.save()
            messages.success(request, 'Técnico adicionado com sucesso!')
            tec = str(t.id)
            return redirect('/tecnicos/lista/?tp=cod&s=' + tec)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'tecnicos/add-tecnico.html', {'form': form, 'error_messages': error_messages})
    else: form = TecnicoForm()
    return render(request, 'tecnicos/add-tecnico.html', {'form': form})

@login_required
def att_tecnico(request, id):
    tec = get_object_or_404(Tecnico, pk=id)
    form = TecnicoForm(instance=tec)
    if not request.user.has_perm('tecnicos.change_tecnico'):
        messages.info(request, 'Você não tem permissão para editar técnicos.')
        return redirect('/tecnicos/lista/')
    if request.method == 'POST':
        form = TecnicoForm(request.POST, instance=tec)
        if form.is_valid():
            tec.save()
            t = str(tec.id)
            messages.success(request, 'Técnico atualizado com sucesso!')
            return redirect('/tecnicos/lista/?tp=cod&s=' + t)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'tecnicos/att-tecnico.html', {'form': form, 'tec': tec, 'error_messages': error_messages})
    else:
        return render(request, 'tecnicos/att-tecnico.html', {'form': form, 'tec': tec})

@login_required
def del_tecnico(request, id):
    if not request.user.has_perm('tecnicos.delete_tecnico'):
        messages.info(request, 'Você não tem permissão para deletar técnicos.')
        return redirect('/tecnicos/lista/')
    tec = get_object_or_404(Tecnico, pk=id)
    tec.delete()
    messages.success(request, 'Técnico deletado com sucesso!')
    return redirect('/tecnicos/lista/')