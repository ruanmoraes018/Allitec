from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Banco
from .forms import BancoForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from filiais.models import Usuario

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('bancos.view_banco')
@login_required
def lista_bancos(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')

    bancos = Banco.objects.filter(vinc_emp=request.user.empresa)


    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        bancos = bancos.filter(banco_normalizado__icontains=norm_s).order_by('nome_banco')
    elif tp == 'cod' and s:
        try:
            bancos = bancos.filter(id__iexact=s).order_by('nome_banco')
        except ValueError:
            bancos = Banco.objects.none()

    if reg == 'todos':
        num_pagina = bancos.count() or 1
    else:
        try:
            num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError:
            num_pagina = 10  # Valor padrão

    paginator = Paginator(bancos, num_pagina)
    page = request.GET.get('page')
    bancos = paginator.get_page(page)

    return render(request, 'bancos/lista.html', {
        'bancos': bancos,
        's': s,
        'tp': tp,
        'reg': reg,
    })

@login_required
def lista_bancos_ajax(request):
    term = request.GET.get('term', '')
    bancos = Banco.objects.filter(nome_banco__icontains=term)[:10]
    data = {'bancos': [{'id': banco.id, 'nome_banco': banco.nome_banco} for banco in bancos]}
    return JsonResponse(data)

@login_required
def add_banco(request):
    if not request.user.has_perm('bancos.add_banco'):
        messages.info(request, 'Você não tem permissão para adicionar bancos.')
        return redirect('/bancos/lista/')
    if request.method == 'POST':
        form = BancoForm(request.POST)
        if form.is_valid():
            b = form.save(commit=False)
            if request.user.is_authenticated:
                try:
                    b.vinc_emp = request.user.filial_user  # Busca a filial do usuário logado
                except Usuario.DoesNotExist:
                    return JsonResponse({'error': 'Usuário não possui filial vinculada'}, status=400)
            b.save()
            messages.success(request, 'Banco adicionado com sucesso!')
            bank = str(b.id)
            return redirect('/bancos/lista/?tp=cod&s=' + bank)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'bancos/add.html', {'form': form, 'error_messages': error_messages})
    else: form = BancoForm()
    return render(request, 'bancos/add.html', {'form': form})

@login_required
def att_banco(request, id):
    b = get_object_or_404(Banco, pk=id)
    form = BancoForm(instance=b)
    if not request.user.has_perm('bancos.change_banco'):
        messages.info(request, 'Você não tem permissão para editar bancos.')
        return redirect('/bancos/lista/')
    if request.method == 'POST':
        form = BancoForm(request.POST, instance=b)
        if form.is_valid():
            b.save()
            bank = str(b.id)
            messages.success(request, 'Banco atualizado com sucesso!')
            return redirect('/bancos/lista/?tp=cod&s=' + bank)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'bancos/att.html', {'form': form, 'b': b, 'error_messages': error_messages})
    else:
        return render(request, 'bancos/att.html', {'form': form, 'b': b})

@login_required
def del_banco(request, id):
    if not request.user.has_perm('bancos.delete_banco'):
        messages.info(request, 'Você não tem permissão para deletar bancos.')
        return redirect('/bancos/lista/')
    b = get_object_or_404(Banco, pk=id)
    b.delete()
    messages.success(request, 'Banco deletado com sucesso!')
    return redirect('/bancos/lista/')