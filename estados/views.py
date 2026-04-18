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
from django.db.models import Q

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('estados.view_estado')
@login_required
def lista_estados(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')
    empresa = request.user.empresa
    estados = Estado.objects.filter(vinc_emp=empresa)

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
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit():
            condicao_busca = Q(nome_estado__icontains=termo_busca) | Q(id=termo_busca)
        else:
            condicao_busca = Q(nome_estado__icontains=termo_busca)
        estados = Estado.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': estado.id, 'text': f"{estado.nome_estado.upper()}"} for estado in estados]
        return JsonResponse({'results': results})
    except Exception as e:
        print(f"Erro na busca AJAX: {e}")
        return JsonResponse({'results': [], 'error': str(e)})

@login_required
def add_estado(request):
    if not request.user.has_perm('estados.add_estado'):
        messages.info(request, 'Você não tem permissão para adicionar estados.')
        return redirect('/estados/lista/')
    if request.method == 'POST':
        form = EstadoForm(request.POST)
        if form.is_valid():
            e = form.save(commit=False)
            e.vinc_emp = request.user.empresa
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
    e = get_object_or_404(Estado, pk=id, vinc_emp=request.user.empresa)
    form = EstadoForm(instance=e)
    if not request.user.has_perm('estados.change_estado'):
        messages.info(request, 'Você não tem permissão para editar estados.')
        return redirect('/estados/lista/')
    if request.method == 'POST':
        form = EstadoForm(request.POST, instance=e)
        if form.is_valid():
            e.save()
            next_url = request.POST.get('next') or request.GET.get('next')
            est = str(e.id)
            messages.success(request, 'Estado atualizado com sucesso!')
            if next_url:
                return redirect(next_url)
            else:
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
    e = get_object_or_404(Estado, pk=id, vinc_emp=request.user.empresa)
    e.delete()
    messages.success(request, 'Estado deletado com sucesso!')
    return redirect('/estados/lista/')