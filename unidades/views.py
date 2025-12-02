from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Unidade
from .forms import UnidadeForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from filiais.models import Usuario

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('unidades.view_unidade')
@login_required
def lista_unidades(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')

    unidades = Unidade.objects.filter(vinc_emp=request.user.empresa)

    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        unidades = unidades.filter(nome_unidade__icontains=norm_s).order_by('nome_unidade')
    elif tp == 'cod' and s:
        try:
            unidades = unidades.filter(id__iexact=s).order_by('nome_unidade')
        except ValueError:
            unidades = Unidade.objects.none()

    if reg == 'todos':
        num_pagina = unidades.count() or 1
    else:
        try:
            num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError:
            num_pagina = 10  # Valor padrão

    paginator = Paginator(unidades, num_pagina)
    page = request.GET.get('page')
    unidades = paginator.get_page(page)

    return render(request, 'unidades/lista.html', {
        'unidades': unidades,
        's': s,
        'tp': tp,
        'reg': reg,
    })

@login_required
def lista_unidades_ajax(request):
    term = request.GET.get('term', '')
    unidades = Unidade.objects.filter(nome_unidade__icontains=term)[:10]
    data = {'unidades': [{'id': unidade.id, 'nome_unidade': unidade.nome_unidade} for unidade in unidades]}
    return JsonResponse(data)

@login_required
def add_unidade(request):
    if not request.user.has_perm('unidades.add_unidade'):
        messages.info(request, 'Você não tem permissão para adicionar unidades.')
        return redirect('/unidades/lista/')
    if request.method == 'POST':
        form = UnidadeForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False)
            if request.user.is_authenticated:
                try:
                    c.vinc_emp = request.user.empresa  # Busca a filial do usuário logado
                except Usuario.DoesNotExist:
                    return JsonResponse({'error': 'Usuário não possui filial vinculada'}, status=400)
            c.save()
            messages.success(request, 'Unidade adicionada com sucesso!')
            cid = str(c.id)
            return redirect('/unidades/lista/?tp=cod&s=' + cid)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'unidades/add.html', {'form': form, 'error_messages': error_messages})
    else: form = UnidadeForm()
    return render(request, 'unidades/add.html', {'form': form})

@login_required
def att_unidade(request, id):
    c = get_object_or_404(Unidade, pk=id)
    form = UnidadeForm(instance=c)
    if not request.user.has_perm('unidades.change_unidade'):
        messages.info(request, 'Você não tem permissão para editar unidades.')
        return redirect('/unidades/lista/')
    if request.method == 'POST':
        form = UnidadeForm(request.POST, instance=c)
        if form.is_valid():
            c.save()
            cid = str(c.id)
            messages.success(request, 'Unidade atualizada com sucesso!')
            return redirect('/unidades/lista/?tp=cod&s=' + cid)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'unidades/att.html', {'form': form, 'c': c, 'error_messages': error_messages})
    else:
        return render(request, 'unidades/att.html', {'form': form, 'c': c})

@login_required
def del_unidade(request, id):
    if not request.user.has_perm('unidades.delete_unidade'):
        messages.info(request, 'Você não tem permissão para deletar unidades.')
        return redirect('/unidades/lista/')
    c = get_object_or_404(Unidade, pk=id)
    c.delete()
    messages.success(request, 'Unidade deletada com sucesso!')
    return redirect('/unidades/lista/')