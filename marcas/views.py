from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Marca
from .forms import MarcaForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from filiais.models import Usuario
from django.views.decorators.http import require_POST
from django.db.models import Q

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('marcas.view_marca')
@login_required
def lista_marcas(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')
    empresa = request.user.empresa
    marcas = Marca.objects.filter(vinc_emp=empresa)

    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        marcas = marcas.filter(nome_marca__icontains=norm_s).order_by('nome_marca')
    elif tp == 'cod' and s:
        try:
            marcas = marcas.filter(id__iexact=s).order_by('nome_marca')
        except ValueError:
            marcas = Marca.objects.none()

    if reg == 'todos':
        num_pagina = marcas.count() or 1
    else:
        try:
            num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError:
            num_pagina = 10  # Valor padrão

    paginator = Paginator(marcas, num_pagina)
    page = request.GET.get('page')
    marcas = paginator.get_page(page)

    return render(request, 'marcas/lista.html', {
        'marcas': marcas,
        's': s,
        'tp': tp,
        'reg': reg,
    })

@login_required
def lista_marcas_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit():
            condicao_busca = Q(nome_marca__icontains=termo_busca) | Q(id=termo_busca)
        else:
            condicao_busca = Q(nome_marca__icontains=termo_busca)
        marcas = Marca.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': marca.id, 'text': f"{marca.nome_marca.upper()}"} for marca in marcas]
        return JsonResponse({'results': results})
    except Exception as e:
        print(f"Erro na busca AJAX: {e}")
        return JsonResponse({'results': [], 'error': str(e)})

@login_required
def add_marca(request):
    if not request.user.has_perm('marcas.add_marca'):
        messages.info(request, 'Você não tem permissão para adicionar marcas.')
        return redirect('/marcas/lista/')
    if request.method == 'POST':
        form = MarcaForm(request.POST)
        if form.is_valid():
            b = form.save(commit=False)
            b.vinc_emp = request.user.empresa
            b.save()
            messages.success(request, 'Marca adicionada com sucesso!')
            bai = str(b.id)
            return redirect('/marcas/lista/?tp=cod&s=' + bai)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'marcas/add.html', {'form': form, 'error_messages': error_messages})
    else: form = MarcaForm()
    return render(request, 'marcas/add.html', {'form': form})

@login_required
@require_POST
def add_marca_ajax(request):
    nome = request.POST.get('nome', '').strip().upper()
    if not nome:
        return JsonResponse({'erro': 'Nome vazio'}, status=400)
    empresa = request.user.empresa
    marca, criada = Marca.objects.get_or_create(
        nome_marca=nome,
        vinc_emp=empresa
    )
    return JsonResponse({
        'id': marca.id,
        'nome': marca.nome_marca,
        'criada': criada
    })

@login_required
def att_marca(request, id):
    b = get_object_or_404(Marca, pk=id, vinc_emp=request.user.empresa)
    form = MarcaForm(instance=b)
    if not request.user.has_perm('marcas.change_marca'):
        messages.info(request, 'Você não tem permissão para editar marcas.')
        return redirect('/marcas/lista/')
    if request.method == 'POST':
        form = MarcaForm(request.POST, instance=b)
        if form.is_valid():
            b.save()
            next_url = request.POST.get('next') or request.GET.get('next')
            bai = str(b.id)
            messages.success(request, 'Marca atualizada com sucesso!')
            if next_url:
                return redirect(next_url)
            else:
                return redirect('/marcas/lista/?tp=cod&s=' + bai)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'marcas/att.html', {'form': form, 'b': b, 'error_messages': error_messages})
    else:
        return render(request, 'marcas/att.html', {'form': form, 'b': b})

@login_required
def del_marca(request, id):
    if not request.user.has_perm('marcas.delete_marca'):
        messages.info(request, 'Você não tem permissão para deletar marcas.')
        return redirect('/marcas/lista/')
    b = get_object_or_404(Marca, pk=id, vinc_emp=request.user.empresa)
    b.delete()
    messages.success(request, 'Marca deletada com sucesso!')
    return redirect('/marcas/lista/')