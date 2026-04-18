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
from django.db.models import Q

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('cidades.view_cidade')
@login_required
def lista_cidades(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')
    empresa = request.user.empresa
    cidades = Cidade.objects.filter(vinc_emp=empresa)

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
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit():
            condicao_busca = Q(nome_cidade__icontains=termo_busca) | Q(id=termo_busca)
        else:
            condicao_busca = Q(nome_cidade__icontains=termo_busca)
        cidades = Cidade.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': cidade.id, 'text': f"{cidade.nome_cidade.upper()}"} for cidade in cidades]
        return JsonResponse({'results': results})
    except Exception as e:
        print(f"Erro na busca AJAX: {e}")
        return JsonResponse({'results': [], 'error': str(e)})

@login_required
def add_cidade(request):
    if not request.user.has_perm('cidades.add_cidade'):
        messages.info(request, 'Você não tem permissão para adicionar cidades.')
        return redirect('/cidades/lista/')
    if request.method == 'POST':
        form = CidadeForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False)
            c.vinc_emp = request.user.empresa
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
    c = get_object_or_404(Cidade, pk=id, vinc_emp=request.user.empresa)
    form = CidadeForm(instance=c)
    if not request.user.has_perm('cidades.change_cidade'):
        messages.info(request, 'Você não tem permissão para editar cidades.')
        return redirect('/cidades/lista/')
    if request.method == 'POST':
        form = CidadeForm(request.POST, instance=c)
        if form.is_valid():
            c.save()
            next_url = request.POST.get('next') or request.GET.get('next')
            cid = str(c.id)
            messages.success(request, 'Cidade atualizada com sucesso!')
            if next_url:
                return redirect(next_url)
            else:
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
    c = get_object_or_404(Cidade, pk=id, vinc_emp=request.user.empresa)
    c.delete()
    messages.success(request, 'Cidade deletada com sucesso!')
    return redirect('/cidades/lista/')