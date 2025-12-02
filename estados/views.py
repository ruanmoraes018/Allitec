from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Estado
from .forms import EstadoForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from filiais.models import Usuario

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('estados.view_estado')
@login_required
def lista_estados(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')

    estados = Estado.objects.filter(vinc_emp=request.user.empresa)

    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        estados = estados.filter(nome_estado__icontains=norm_s).order_by('nome_estado')
    elif tp == 'cod' and s:
        try:
            estados = estados.filter(id__iexact=s).order_by('nome_estado')
        except ValueError:
            estados = Estado.objects.none()

    if reg == 'todos':
        num_pagina = estados.count() or 1
    else:
        try:
            num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError:
            num_pagina = 10  # Valor padrão

    paginator = Paginator(estados, num_pagina)
    page = request.GET.get('page')
    estados = paginator.get_page(page)

    return render(request, 'estados/lista.html', {
        'estados': estados,
        's': s,
        'tp': tp,
        'reg': reg,
    })

@login_required
def lista_estados_ajax(request):
    term = request.GET.get('term', '')
    estados = Estado.objects.filter(nome_estado__icontains=term)[:10]
    data = {'estados': [{'id': estado.id, 'nome_estado': estado.nome_estado} for estado in estados]}
    return JsonResponse(data)

@login_required
def add_estado(request):
    if not request.user.has_perm('estados.add_estado'):
        messages.info(request, 'Você não tem permissão para adicionar estados.')
        return redirect('/estados/lista/')
    if request.method == 'POST':
        form = EstadoForm(request.POST)
        if form.is_valid():
            e = form.save(commit=False)
            if request.user.is_authenticated:
                try:
                    e.vinc_emp = request.user.empresa  # Busca a filial do usuário logado
                except Usuario.DoesNotExist:
                    return JsonResponse({'error': 'Usuário não possui filial vinculada'}, status=400)
            e.save()
            messages.success(request, 'Estado adicionado com sucesso!')
            est = str(e.id)
            return redirect('/estados/lista/?tp=cod&s=' + est)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'estados/add.html', {'form': form, 'error_messages': error_messages})
    else: form = EstadoForm()
    return render(request, 'estados/add.html', {'form': form})

@login_required
def att_estado(request, id):
    e = get_object_or_404(Estado, pk=id)
    form = EstadoForm(instance=e)
    if not request.user.has_perm('estados.change_estado'):
        messages.info(request, 'Você não tem permissão para editar estados.')
        return redirect('/estados/lista/')
    if request.method == 'POST':
        form = EstadoForm(request.POST, instance=e)
        if form.is_valid():
            e.save()
            est = str(e.id)
            messages.success(request, 'Estado atualizado com sucesso!')
            return redirect('/estados/lista/?tp=cod&s=' + est)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'estados/att.html', {'form': form, 'e': e, 'error_messages': error_messages})
    else:
        return render(request, 'estados/att.html', {'form': form, 'e': e})

@login_required
def del_estado(request, id):
    if not request.user.has_perm('estados.delete_estado'):
        messages.info(request, 'Você não tem permissão para deletar estados.')
        return redirect('/estados/lista/')
    e = get_object_or_404(Estado, pk=id)
    e.delete()
    messages.success(request, 'Estado deletado com sucesso!')
    return redirect('/estados/lista/')