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
from django.db.models import Q

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('unidades.view_unidade')
@login_required
def lista_unidades(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')
    empresa = request.user.empresa
    unidades = Unidade.objects.filter(vinc_emp=empresa)

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
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit():
            condicao_busca = Q(nome_unidade__icontains=termo_busca) | Q(id=termo_busca)
        else:
            condicao_busca = Q(nome_unidade__icontains=termo_busca)
        unidades = Unidade.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': unidade.id, 'text': f"{unidade.nome_unidade.upper()}"} for unidade in unidades]
        return JsonResponse({'results': results})
    except Exception as e:
        print(f"Erro na busca AJAX: {e}")
        return JsonResponse({'results': [], 'error': str(e)})


@login_required
def add_unidade(request):
    if not request.user.has_perm('unidades.add_unidade'):
        messages.info(request, 'Você não tem permissão para adicionar unidades.')
        return redirect('/unidades/lista/')
    if request.method == 'POST':
        form = UnidadeForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False)
            c.vinc_emp = request.user.empresa
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
    c = get_object_or_404(Unidade, pk=id, vinc_emp=request.user.empresa)
    form = UnidadeForm(instance=c)
    if not request.user.has_perm('unidades.change_unidade'):
        messages.info(request, 'Você não tem permissão para editar unidades.')
        return redirect('/unidades/lista/')
    if request.method == 'POST':
        form = UnidadeForm(request.POST, instance=c)
        if form.is_valid():
            c = form.save(commit=False)
            c.save()
            cid = str(c.id)
            messages.success(request, 'Unidade atualizada com sucesso!')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            else:
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
    c = get_object_or_404(Unidade, pk=id, vinc_emp=request.user.empresa)
    c.delete()
    messages.success(request, 'Unidade deletada com sucesso!')
    return redirect('/unidades/lista/')