from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Unidade
from .forms import UnidadeForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from django.db.models import Q
from django.views.decorators.http import require_POST
from util.logs import gerar_alteracoes, registrar_log

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
        try: unidades = unidades.filter(codigo__iexact=s).order_by('nome_unidade')
        except ValueError: unidades = Unidade.objects.none()
    if reg == 'todos': num_pagina = unidades.count() or 1
    else:
        try: num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError: num_pagina = 10  # Valor padrão
    paginator = Paginator(unidades, num_pagina)
    page = request.GET.get('page')
    unidades = paginator.get_page(page)
    return render(request, 'unidades/lista.html', {'unidades': unidades, 's': s, 'tp': tp, 'reg': reg,})

@login_required
def lista_unidades_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit(): condicao_busca = Q(nome_unidade__icontains=termo_busca) | Q(codigo=termo_busca)
        else: condicao_busca = Q(nome_unidade__icontains=termo_busca)
        unidades = Unidade.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': unidade.codigo, 'text': f"{unidade.nome_unidade.upper()}"} for unidade in unidades]
        return JsonResponse({'results': results})
    except Exception as e: return JsonResponse({'results': [], 'error': str(e)})

@login_required
def add_unidade(request):
    if not request.user.has_perm('unidades.add_unidade'):
        messages.info(request, 'Você não tem permissão para adicionar unidades.')
        return redirect('/unidades/lista/')
    if request.method == 'POST':
        form = UnidadeForm(request.POST)
        if form.is_valid():
            nome = form.cleaned_data['nome_unidade'].strip().upper()
            empresa = request.user.empresa
            # Verifica duplicata antes de salvar
            if Unidade.objects.filter(nome_unidade=nome, vinc_emp=empresa).exists():
                messages.warning(request, f'A unidade "{nome}" já está cadastrada.')
                return render(request, 'unidades/add.html', {'form': form})
            b = form.save(commit=False)
            b.nome_unidade = nome
            b.vinc_emp = empresa
            b.save()
            registrar_log(request, "CRIAR", "Unidade", b.nome_unidade, f"Adicionou a unidade: {b.codigo} - {b.nome_unidade}", b.id, gerar_alteracoes(obj_novo=b))
            messages.success(request, 'Unidade adicionada com sucesso!')
            return redirect('/unidades/lista/?tp=cod&s=' + str(b.codigo))
        else:
            error_messages = [f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!" for field in form if field.errors]
            return render(request, 'unidades/add.html', {'form': form, 'error_messages': error_messages})
    else:
        form = UnidadeForm()
    return render(request, 'unidades/add.html', {'form': form})

@login_required
@require_POST
def add_unidade_ajax(request):
    nome = request.POST.get('nome', '').strip().upper()
    if not nome:
        return JsonResponse({'erro': 'Nome vazio'}, status=400)
    empresa = request.user.empresa
    unidade, criado = Unidade.objects.get_or_create(nome_unidade=nome, vinc_emp=empresa)
    if criado:
        registrar_log(request, "CRIAR", "Unidade", unidade.nome_unidade, f"Adicionou a unidade: {unidade.codigo} - {unidade.nome_unidade}", unidade.id, gerar_alteracoes(obj_novo=unidade))
    return JsonResponse({'id': unidade.codigo, 'nome': unidade.nome_unidade, 'criado': criado})

@login_required
def att_unidade(request, codigo):
    b = get_object_or_404(Unidade, codigo=codigo, vinc_emp=request.user.empresa)
    if not request.user.has_perm('unidades.change_unidade'):
        messages.info(request, 'Você não tem permissão para editar unidades.')
        return redirect('/unidades/lista/')
    it_old = Unidade.objects.get(codigo=b.codigo, vinc_emp=request.user.empresa)
    form = UnidadeForm(instance=b)
    if request.method == 'POST':
        form = UnidadeForm(request.POST, instance=b)
        if form.is_valid():
            nome = form.cleaned_data['nome_unidade'].strip().upper()
            empresa = request.user.empresa
            # Verifica duplicata excluindo o próprio registro
            if Unidade.objects.filter(nome_unidade=nome, vinc_emp=empresa).exclude(codigo=codigo).exists():
                messages.warning(request, f'A unidade "{nome}" já está cadastrada.')
                return render(request, 'unidades/att.html', {'form': form, 'b': b})
            b = form.save(commit=False)
            b.nome_unidade = nome
            b.vinc_emp = empresa
            b.save()
            registrar_log(request, "ALTERAR", "Unidade", b.nome_unidade, f"Alterou a unidade: {b.codigo} - {b.nome_unidade}",  b.id, gerar_alteracoes(it_old, b))
            messages.success(request, 'Unidade atualizada com sucesso!')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('/unidades/lista/?tp=cod&s=' + str(b.codigo))
        else:
            error_messages = [f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!" for field in form if field.errors]
            return render(request, 'unidades/att.html', {'form': form, 'b': b, 'error_messages': error_messages})
    return render(request, 'unidades/att.html', {'form': form, 'b': b})

@login_required
def del_unidade(request, codigo):
    if not request.user.has_perm('unidades.delete_unidade'):
        messages.info(request, 'Você não tem permissão para deletar unidades.')
        return redirect('/unidades/lista/')
    c = get_object_or_404(Unidade, codigo=codigo, vinc_emp=request.user.empresa)
    registrar_log(
        request, "EXCLUIR", "Unidade", c.nome_unidade,
        f"Excluiu a unidade: {c.codigo} - {c.nome_unidade}",
        c.id, gerar_alteracoes(obj_antigo=c)
    )
    c.delete()
    messages.success(request, 'Unidade deletada com sucesso!')
    return redirect('/unidades/lista/')