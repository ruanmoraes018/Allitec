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
from django.db.models import Q

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('tabelas_preco.view_tabelapreco')
@login_required
def lista_tabelas_preco(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')
    empresa = request.user.empresa
    tabelas_preco = TabelaPreco.objects.filter(vinc_emp=empresa)
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
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit():
            condicao_busca = Q(descricao__icontains=termo_busca) | Q(id=termo_busca)
        else:
            condicao_busca = Q(descricao__icontains=termo_busca)
        tabelas_preco = TabelaPreco.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': tabela_preco.id, 'text': f"{tabela_preco.descricao.upper()}"} for tabela_preco in tabelas_preco]
        return JsonResponse({'results': results})
    except Exception as e:
        print(f"Erro na busca AJAX: {e}")
        return JsonResponse({'results': [], 'error': str(e)})

@login_required
def get_tabela_preco(request):
    tabela_id = request.GET.get("id")
    try:
        tabela = TabelaPreco.objects.get(pk=tabela_id, vinc_emp=request.user.empresa)
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
            c.vinc_emp = request.user.empresa
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
    c = get_object_or_404(TabelaPreco, pk=id, vinc_emp=request.user.empresa)
    form = TabelaPrecoForm(instance=c)
    if not request.user.has_perm('tabelas_preco.change_tabelapreco'):
        messages.info(request, 'Você não tem permissão para editar tabelas de preço.')
        return redirect('/tabelas_preco/lista/')
    if request.method == 'POST':
        form = TabelaPrecoForm(request.POST, instance=c)
        if form.is_valid():
            c = form.save(commit=False)
            c.save()
            cid = str(c.id)
            messages.success(request, 'Tabela de Preço atualizada com sucesso!')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            else:
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
    c = get_object_or_404(TabelaPreco, pk=id, vinc_emp=request.user.empresa)
    c.delete()
    messages.success(request, 'Tabela de Preço deletada com sucesso!')
    return redirect('/tabelas_preco/lista/')