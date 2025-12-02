from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Cidade
from .forms import CidadeForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from filiais.models import Usuario

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('cidades.view_cidade')
@login_required
def lista_cidades(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')

    cidades = Cidade.objects.filter(vinc_emp=request.user.empresa)

    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        cidades = cidades.filter(nome_cidade__icontains=norm_s).order_by('nome_cidade')
    elif tp == 'cod' and s:
        try:
            cidades = cidades.filter(id__iexact=s).order_by('nome_cidade')
        except ValueError:
            cidades = Cidade.objects.none()

    if reg == 'todos':
        num_pagina = cidades.count() or 1
    else:
        try:
            num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError:
            num_pagina = 10  # Valor padrão

    paginator = Paginator(cidades, num_pagina)
    page = request.GET.get('page')
    cidades = paginator.get_page(page)

    return render(request, 'cidades/lista.html', {
        'cidades': cidades,
        's': s,
        'tp': tp,
        'reg': reg,
    })

@login_required
def lista_cidades_ajax(request):
    term = request.GET.get('term', '')
    cidades = Cidade.objects.filter(nome_cidade__icontains=term)[:10]
    data = {'cidades': [{'id': cidade.id, 'nome_cidade': cidade.nome_cidade} for cidade in cidades]}
    return JsonResponse(data)

@login_required
def add_cidade(request):
    if not request.user.has_perm('cidades.add_cidade'):
        messages.info(request, 'Você não tem permissão para adicionar cidades.')
        return redirect('/cidades/lista/')
    if request.method == 'POST':
        form = CidadeForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False)
            if request.user.is_authenticated:
                try:
                    c.vinc_emp = request.user.empresa  # Busca a filial do usuário logado
                except Usuario.DoesNotExist:
                    return JsonResponse({'error': 'Usuário não possui filial vinculada'}, status=400)
            c.save()
            messages.success(request, 'Cidade adicionada com sucesso!')
            cid = str(c.id)
            return redirect('/cidades/lista/?tp=cod&s=' + cid)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'cidades/add.html', {'form': form, 'error_messages': error_messages})
    else: form = CidadeForm()
    return render(request, 'cidades/add.html', {'form': form})

@login_required
def att_cidade(request, id):
    c = get_object_or_404(Cidade, pk=id)
    form = CidadeForm(instance=c)
    if not request.user.has_perm('cidades.change_cidade'):
        messages.info(request, 'Você não tem permissão para editar cidades.')
        return redirect('/cidades/lista/')
    if request.method == 'POST':
        form = CidadeForm(request.POST, instance=c)
        if form.is_valid():
            c.save()
            cid = str(c.id)
            messages.success(request, 'Cidade atualizada com sucesso!')
            return redirect('/cidades/lista/?tp=cod&s=' + cid)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'cidades/att.html', {'form': form, 'c': c, 'error_messages': error_messages})
    else:
        return render(request, 'cidades/att.html', {'form': form, 'c': c})

@login_required
def del_cidade(request, id):
    if not request.user.has_perm('cidades.delete_cidade'):
        messages.info(request, 'Você não tem permissão para deletar cidades.')
        return redirect('/cidades/lista/')
    c = get_object_or_404(Cidade, pk=id)
    c.delete()
    messages.success(request, 'Cidade deletada com sucesso!')
    return redirect('/cidades/lista/')