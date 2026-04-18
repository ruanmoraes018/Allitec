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
from django.db.models import Q

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('bancos.view_banco')
@login_required
def lista_bancos(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')
    empresa = request.user.empresa
    bancos = Banco.objects.filter(vinc_emp=empresa)
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
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit():
            condicao_busca = Q(nome_banco__icontains=termo_busca) | Q(id=termo_busca)
        else:
            condicao_busca = Q(nome_banco__icontains=termo_busca)
        bancos = Banco.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': banco.id, 'text': f"{banco.id} - {banco.nome_banco.upper()}"} for banco in bancos]
        return JsonResponse({'results': results})
    except Exception as e:
        print(f"Erro na busca AJAX: {e}")
        return JsonResponse({'results': [], 'error': str(e)})
    
@login_required
def add_banco(request):
    if not request.user.has_perm('bancos.add_banco'):
        messages.info(request, 'Você não tem permissão para adicionar bancos.')
        return redirect('/bancos/lista/')
    if request.method == 'POST':
        form = BancoForm(request.POST)
        if form.is_valid():
            b = form.save(commit=False)
            b.vinc_emp = request.user.empresa
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
        form = BancoForm(request.POST, instance=b, vinc_emp=request.user.empresa)
        if form.is_valid():
            b.save()
            next_url = request.POST.get('next') or request.GET.get('next')
            bank = str(b.id)
            messages.success(request, 'Banco atualizado com sucesso!')
            if next_url:
                return redirect(next_url)
            else:
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
    b = get_object_or_404(Banco, pk=id, vinc_emp=request.user.empresa)
    b.delete()
    messages.success(request, 'Banco deletado com sucesso!')
    return redirect('/bancos/lista/')