from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Grupo
from .forms import GrupoForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from filiais.models import Usuario

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('grupos.view_grupo')
@login_required
def lista_grupos(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')

    grupos = Grupo.objects.filter(vinc_emp=request.user.empresa)

    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        grupos = grupos.filter(nome_grupo__icontains=norm_s).order_by('nome_grupo')
    elif tp == 'cod' and s:
        try:
            grupos = grupos.filter(id__iexact=s).order_by('nome_grupo')
        except ValueError:
            grupos = Grupo.objects.none()

    if reg == 'todos':
        num_pagina = grupos.count() or 1
    else:
        try:
            num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError:
            num_pagina = 10  # Valor padrão

    paginator = Paginator(grupos, num_pagina)
    page = request.GET.get('page')
    grupos = paginator.get_page(page)

    return render(request, 'grupos/lista.html', {
        'grupos': grupos,
        's': s,
        'tp': tp,
        'reg': reg,
    })

@login_required
def lista_grupos_ajax(request):
    term = request.GET.get('term', '')
    grupos = Grupo.objects.filter(nome_grupo__icontains=term)[:10]
    data = {'grupos': [{'id': grupo.id, 'nome_grupo': grupo.nome_grupo} for grupo in grupos]}
    return JsonResponse(data)

@login_required
def add_grupo(request):
    if not request.user.has_perm('grupos.add_grupo'):
        messages.info(request, 'Você não tem permissão para adicionar grupos.')
        return redirect('/grupos/lista/')
    if request.method == 'POST':
        form = GrupoForm(request.POST)
        if form.is_valid():
            g = form.save(commit=False)
            if request.user.is_authenticated:
                try:
                    g.vinc_emp = request.user.empresa  # Busca a filial do usuário logado
                except Usuario.DoesNotExist:
                    return JsonResponse({'error': 'Usuário não possui filial vinculada'}, status=400)
            g.save()
            messages.success(request, 'Grupo adicionado com sucesso!')
            gp = str(g.id)
            return redirect('/grupos/lista/?tp=cod&s=' + gp)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'grupos/add.html', {'form': form, 'error_messages': error_messages})
    else: form = GrupoForm()
    return render(request, 'grupos/add.html', {'form': form})

@login_required
def att_grupo(request, id):
    g = get_object_or_404(Grupo, pk=id)
    form = GrupoForm(instance=g)
    if not request.user.has_perm('grupos.change_grupo'):
        messages.info(request, 'Você não tem permissão para editar grupos.')
        return redirect('/grupos/lista/')
    if request.method == 'POST':
        form = GrupoForm(request.POST, instance=g)
        if form.is_valid():
            g.save()
            gp = str(g.id)
            messages.success(request, 'Grupo atualizado com sucesso!')
            return redirect('/grupos/lista/?tp=cod&s=' + gp)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'grupos/att.html', {'form': form, 'g': g, 'error_messages': error_messages})
    else:
        return render(request, 'grupos/att.html', {'form': form, 'g': g})

@login_required
def del_grupo(request, id):
    if not request.user.has_perm('grupos.delete_grupo'):
        messages.info(request, 'Você não tem permissão para deletar grupos.')
        return redirect('/grupos/lista/')
    g = get_object_or_404(Grupo, pk=id)
    g.delete()
    messages.success(request, 'Grupo deletado com sucesso!')
    return redirect('/grupos/lista/')