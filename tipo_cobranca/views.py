from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import TipoCobranca
from .forms import TipoCobrancaForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from filiais.models import Usuario
from django.db.models import Q

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('tipo_cobranca.view_tipocobranca')
@login_required
def lista_tp_cobrancas(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')
    empresa = request.user.empresa
    tp_cobrancas = TipoCobranca.objects.filter(vinc_emp=empresa)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        tp_cobrancas = tp_cobrancas.filter(descricao__icontains=norm_s).order_by('descricao')
    elif tp == 'cod' and s:
        try:
            tp_cobrancas = tp_cobrancas.filter(id__iexact=s).order_by('descricao')
        except ValueError:
            tp_cobrancas = TipoCobranca.objects.none()
    if reg == 'todos':
        num_pagina = tp_cobrancas.count() or 1
    else:
        try:
            num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError:
            num_pagina = 10  # Valor padrão
    paginator = Paginator(tp_cobrancas, num_pagina)
    page = request.GET.get('page')
    tp_cobrancas = paginator.get_page(page)
    return render(request, 'tp_cobrancas/lista.html', {
        'tp_cobrancas': tp_cobrancas,
        's': s,
        'tp': tp,
        'reg': reg,
    })

@login_required
def lista_tp_cobrancas_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit():
            condicao_busca = Q(descricao__icontains=termo_busca) | Q(id=termo_busca)
        else:
            condicao_busca = Q(descricao__icontains=termo_busca)
        tp_cobrancas = TipoCobranca.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': tp_cobranca.id, 'text': f"{tp_cobranca.descricao.upper()}"} for tp_cobranca in tp_cobrancas]
        return JsonResponse({'results': results})
    except Exception as e:
        print(f"Erro na busca AJAX: {e}")
        return JsonResponse({'results': [], 'error': str(e)})

@login_required
def add_tp_cobranca(request):
    if not request.user.has_perm('tipo_cobranca.add_tipocobranca'):
        messages.info(request, 'Você não tem permissão para adicionar tipos de cobrança.')
        return redirect('/tp_cobrancas/lista/')
    if request.method == 'POST':
        form = TipoCobrancaForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False)
            c.vinc_emp = request.user.empresa
            c.save()
            messages.success(request, 'Tipo de Cobrança adicionado com sucesso!')
            cid = str(c.id)
            return redirect('/tp_cobrancas/lista/?tp=cod&s=' + cid)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'tp_cobrancas/add.html', {'form': form, 'error_messages': error_messages})
    else: form = TipoCobrancaForm()
    return render(request, 'tp_cobrancas/add.html', {'form': form})

@login_required
def att_tp_cobranca(request, id):
    c = get_object_or_404(TipoCobranca, pk=id, vinc_emp=request.user.empresa)
    form = TipoCobrancaForm(instance=c)
    if not request.user.has_perm('tipo_cobranca.change_tipocobranca'):
        messages.info(request, 'Você não tem permissão para editar tipos de cobrança.')
        return redirect('/tp_cobrancas/lista/')
    if request.method == 'POST':
        form = TipoCobrancaForm(request.POST, instance=c)
        if form.is_valid():
            c = form.save(commit=False)
            c.save()
            cid = str(c.id)
            messages.success(request, 'Tipo de Cobrança atualizado com sucesso!')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            else:
                return redirect('/tp_cobrancas/lista/?tp=cod&s=' + cid)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'tp_cobrancas/att.html', {'form': form, 'c': c, 'error_messages': error_messages})
    else:
        return render(request, 'tp_cobrancas/att.html', {'form': form, 'c': c})

@login_required
def del_tp_cobranca(request, id):
    if not request.user.has_perm('tipo_cobranca.delete_tipocobranca'):
        messages.info(request, 'Você não tem permissão para deletar tipos de cobrança.')
        return redirect('/tp_cobrancas/lista/')
    c = get_object_or_404(TipoCobranca, pk=id, vinc_emp=request.user.empresa)
    c.delete()
    messages.success(request, 'Tipo de Cobrança deletado com sucesso!')
    return redirect('/tp_cobrancas/lista/')