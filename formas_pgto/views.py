from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import FormaPgto
from .forms import FormaPgtoForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from filiais.models import Usuario

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('formas_pgto.view_formapgto')
@login_required
def lista_formas_pgto(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')

    formas_pgto = FormaPgto.objects.filter(vinc_emp=request.user.empresa)

    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        formas_pgto = formas_pgto.filter(descricao__icontains=norm_s).order_by('descricao')
    elif tp == 'cod' and s:
        try:
            formas_pgto = formas_pgto.filter(id__iexact=s).order_by('descricao')
        except ValueError:
            formas_pgto = FormaPgto.objects.none()

    if reg == 'todos':
        num_pagina = formas_pgto.count() or 1
    else:
        try:
            num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError:
            num_pagina = 10  # Valor padrão

    paginator = Paginator(formas_pgto, num_pagina)
    page = request.GET.get('page')
    formas_pgto = paginator.get_page(page)

    return render(request, 'formas_pgto/lista.html', {
        'formas_pgto': formas_pgto,
        's': s,
        'tp': tp,
        'reg': reg,
    })

@login_required
def lista_formas_pgto_ajax(request):
    term = request.GET.get('term', '')
    formas_pgto = FormaPgto.objects.filter(descricao__icontains=term)[:10]
    data = {'formas_pgto': [{'id': forma_pgto.id, 'descricao': forma_pgto.descricao} for forma_pgto in formas_pgto]}
    return JsonResponse(data)

def get_forma_pgto(request):
    forma_id = request.GET.get("id")
    try:
        forma = FormaPgto.objects.get(pk=forma_id)
        return JsonResponse({"id": forma.id, "descricao": forma.descricao})
    except FormaPgto.DoesNotExist:
        return JsonResponse({"error": "Forma não encontrada"}, status=404)

@login_required
def add_formas_pgto(request):
    if not request.user.has_perm('formas_pgto.add_formapgto'):
        messages.info(request, 'Você não tem permissão para adicionar formas de pagamento.')
        return redirect('/formas_pgto/lista/')
    if request.method == 'POST':
        form = FormaPgtoForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False)
            if request.user.is_authenticated:
                try:
                    c.vinc_emp = request.user.empresa  # Busca a filial do usuário logado
                except Usuario.DoesNotExist:
                    return JsonResponse({'error': 'Usuário não possui filial vinculada'}, status=400)
            c.save()
            messages.success(request, 'Forma de Pagamento adicionada com sucesso!')
            cid = str(c.id)
            return redirect('/formas_pgto/lista/?tp=cod&s=' + cid)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'formas_pgto/add.html', {'form': form, 'error_messages': error_messages})
    else: form = FormaPgtoForm()
    return render(request, 'formas_pgto/add.html', {'form': form})

@login_required
def att_formas_pgto(request, id):
    c = get_object_or_404(FormaPgto, pk=id)
    form = FormaPgtoForm(instance=c)
    if not request.user.has_perm('formas_pgto.change_formapgto'):
        messages.info(request, 'Você não tem permissão para editar formas de pagamento.')
        return redirect('/formas_pgto/lista/')
    if request.method == 'POST':
        form = FormaPgtoForm(request.POST, instance=c)
        if form.is_valid():
            c.save()
            cid = str(c.id)
            messages.success(request, 'Forma de Pagamento atualizada com sucesso!')
            return redirect('/formas_pgto/lista/?tp=cod&s=' + cid)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'formas_pgto/att.html', {'form': form, 'c': c, 'error_messages': error_messages})
    else:
        return render(request, 'formas_pgto/att.html', {'form': form, 'c': c})

@login_required
def del_formas_pgto(request, id):
    if not request.user.has_perm('formas_pgto.delete_formapgto'):
        messages.info(request, 'Você não tem permissão para deletar formas de pagamento.')
        return redirect('/formas_pgto/lista/')
    c = get_object_or_404(FormaPgto, pk=id)
    c.delete()
    messages.success(request, 'Forma de Pagamento deletada com sucesso!')
    return redirect('/formas_pgto/lista/')