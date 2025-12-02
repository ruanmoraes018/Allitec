from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import TabelaPreco
from .forms import TabelaPrecoForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from filiais.models import Usuario

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('tabelas_preco.view_tabelapreco')
@login_required
def lista_tabelas_preco(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')

    tabelas_preco = TabelaPreco.objects.filter(vinc_emp=request.user.empresa)

    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        tabelas_preco = tabelas_preco.filter(descricao__icontains=norm_s).order_by('descricao')
    elif tp == 'cod' and s:
        try:
            tabelas_preco = tabelas_preco.filter(id__iexact=s).order_by('descricao')
        except ValueError:
            tabelas_preco = TabelaPreco.objects.none()

    if reg == 'todos':
        num_pagina = tabelas_preco.count() or 1
    else:
        try:
            num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError:
            num_pagina = 10  # Valor padrão

    paginator = Paginator(tabelas_preco, num_pagina)
    page = request.GET.get('page')
    tabelas_preco = paginator.get_page(page)

    return render(request, 'tabelas_preco/lista.html', {
        'tabelas_preco': tabelas_preco,
        's': s,
        'tp': tp,
        'reg': reg,
    })

@login_required
def lista_tabelas_preco_ajax(request):
    term = request.GET.get('term', '')
    tabelas_preco = TabelaPreco.objects.filter(descricao__icontains=term)[:10]
    data = {'tabelas_preco': [{'id': tabela_preco.id, 'descricao': tabela_preco.descricao} for tabela_preco in tabelas_preco]}
    return JsonResponse(data)

def get_tabela_preco(request):
    tabela_id = request.GET.get("id")
    try:
        tabela = TabelaPreco.objects.get(pk=tabela_id)
        return JsonResponse({"id": tabela.id, "descricao": tabela.descricao, "margem": tabela.margem})
    except TabelaPreco.DoesNotExist:
        return JsonResponse({"error": "Tabela não encontrada"}, status=404)

@login_required
def add_tabelas_preco(request):
    if not request.user.has_perm('tabelas_preco.add_tabelapreco'):
        messages.info(request, 'Você não tem permissão para adicionar tabelas de preço.')
        return redirect('/tabelas_preco/lista/')
    if request.method == 'POST':
        form = TabelaPrecoForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False)
            if request.user.is_authenticated:
                try:
                    c.vinc_emp = request.user.empresa  # Busca a filial do usuário logado
                except Usuario.DoesNotExist:
                    return JsonResponse({'error': 'Usuário não possui filial vinculada'}, status=400)
            c.save()
            messages.success(request, 'Tabela de Preço adicionada com sucesso!')
            cid = str(c.id)
            return redirect('/tabelas_preco/lista/?tp=cod&s=' + cid)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'tabelas_preco/add.html', {'form': form, 'error_messages': error_messages})
    else: form = TabelaPrecoForm()
    return render(request, 'tabelas_preco/add.html', {'form': form})

@login_required
def att_tabelas_preco(request, id):
    c = get_object_or_404(TabelaPreco, pk=id)
    form = TabelaPrecoForm(instance=c)
    if not request.user.has_perm('tabelas_preco.change_tabelapreco'):
        messages.info(request, 'Você não tem permissão para editar tabelas de preço.')
        return redirect('/tabelas_preco/lista/')
    if request.method == 'POST':
        form = TabelaPrecoForm(request.POST, instance=c)
        if form.is_valid():
            c.save()
            cid = str(c.id)
            messages.success(request, 'Tabela de Preço atualizada com sucesso!')
            return redirect('/tabelas_preco/lista/?tp=cod&s=' + cid)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'tabelas_preco/att.html', {'form': form, 'c': c, 'error_messages': error_messages})
    else:
        return render(request, 'tabelas_preco/att.html', {'form': form, 'c': c})

@login_required
def del_tabelas_preco(request, id):
    if not request.user.has_perm('tabelas_preco.delete_tabelapreco'):
        messages.info(request, 'Você não tem permissão para deletar tabelas de preço.')
        return redirect('/tabelas_preco/lista/')
    c = get_object_or_404(TabelaPreco, pk=id)
    c.delete()
    messages.success(request, 'Tabela de Preço deletada com sucesso!')
    return redirect('/tabelas_preco/lista/')