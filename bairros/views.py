from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Bairro
from .forms import BairroForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from filiais.models import Usuario

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('bairros.view_bairro')
@login_required
def lista_bairros(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')

    bairros = Bairro.objects.filter(vinc_emp=request.user.empresa)

    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        bairros = bairros.filter(nome_bairro__icontains=norm_s).order_by('nome_bairro')
    elif tp == 'cod' and s:
        try:
            bairros = bairros.filter(id__iexact=s).order_by('nome_bairro')
        except ValueError:
            bairros = Bairro.objects.none()

    if reg == 'todos':
        num_pagina = bairros.count() or 1
    else:
        try:
            num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError:
            num_pagina = 10  # Valor padrão

    paginator = Paginator(bairros, num_pagina)
    page = request.GET.get('page')
    bairros = paginator.get_page(page)

    return render(request, 'bairros/lista.html', {
        'bairros': bairros,
        's': s,
        'tp': tp,
        'reg': reg,
    })

@login_required
def lista_bairros_ajax(request):
    term = request.GET.get('term', '')
    bairros = Bairro.objects.filter(nome_bairro__icontains=term)[:10]
    data = {'bairros': [{'id': bairro.id, 'nome_bairro': bairro.nome_bairro} for bairro in bairros]}
    return JsonResponse(data)

@login_required
def add_bairro(request):
    if not request.user.has_perm('bairros.add_bairro'):
        messages.info(request, 'Você não tem permissão para adicionar bairros.')
        return redirect('/bairros/lista/')
    if request.method == 'POST':
        form = BairroForm(request.POST)
        if form.is_valid():
            b = form.save(commit=False)
            if request.user.is_authenticated:
                try:
                    b.vinc_emp = request.user.empresa  # Busca a filial do usuário logado
                except Usuario.DoesNotExist:
                    return JsonResponse({'error': 'Usuário não possui filial vinculada'}, status=400)
            b.save()
            messages.success(request, 'Bairro adicionado com sucesso!')
            bai = str(b.id)
            return redirect('/bairros/lista/?tp=cod&s=' + bai)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'bairros/add.html', {'form': form, 'error_messages': error_messages})
    else: form = BairroForm()
    return render(request, 'bairros/add.html', {'form': form})

@login_required
def att_bairro(request, id):
    b = get_object_or_404(Bairro, pk=id)
    form = BairroForm(instance=b)
    if not request.user.has_perm('bairros.change_bairro'):
        messages.info(request, 'Você não tem permissão para editar bairros.')
        return redirect('/bairros/lista/')
    if request.method == 'POST':
        form = BairroForm(request.POST, instance=b)
        if form.is_valid():
            b.save()
            bai = str(b.id)
            messages.success(request, 'Bairro atualizado com sucesso!')
            return redirect('/bairros/lista/?tp=cod&s=' + bai)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'bairros/att.html', {'form': form, 'b': b, 'error_messages': error_messages})
    else:
        return render(request, 'bairros/att.html', {'form': form, 'b': b})

@login_required
def del_bairro(request, id):
    if not request.user.has_perm('bairros.delete_bairro'):
        messages.info(request, 'Você não tem permissão para deletar bairros.')
        return redirect('/bairros/lista/')
    b = get_object_or_404(Bairro, pk=id)
    b.delete()
    messages.success(request, 'Bairro deletado com sucesso!')
    return redirect('/bairros/lista/')