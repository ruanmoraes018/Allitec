from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Informacoes
from .forms import InformacoesForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from filiais.models import Usuario
from django.db.models import Q
from util.logs import gerar_alteracoes, registrar_log

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('informacoes.view_informacoes')
@login_required
def lista_informacoes(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')
    empresa = request.user.empresa
    informacoes = Informacoes.objects.filter(empresa=empresa)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        informacoes = informacoes.filter(descricao__icontains=norm_s).order_by('descricao')
    elif tp == 'cod' and s:
        try: informacoes = informacoes.filter(codigo__iexact=s).order_by('descricao')
        except ValueError: informacoes = Informacoes.objects.none()
    if reg == 'todos': num_pagina = informacoes.count() or 1
    else:
        try: num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError: num_pagina = 10  # Valor padrão
    paginator = Paginator(informacoes, num_pagina)
    page = request.GET.get('page')
    informacoes = paginator.get_page(page)
    return render(request, 'informacoes/lista.html', {'informacoes': informacoes, 's': s, 'tp': tp, 'reg': reg,})

@login_required
def lista_informacoes_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit(): condicao_busca = Q(descricao__icontains=termo_busca) | Q(codigo=termo_busca)
        else: condicao_busca = Q(descricao__icontains=termo_busca)
        informacoes = Informacoes.objects.filter(condicao_busca & Q(empresa=empresa))[:20]
        results = [{'id': informacoes.codigo, 'text': f"{informacoes.descricao.upper()}"} for informacoes in informacoes]
        return JsonResponse({'results': results})
    except Exception as e:
        return JsonResponse({'results': [], 'error': str(e)})

@login_required
def add_informacao(request):
    if not request.user.has_perm('informacoes.add_informacoes'):
        messages.info(request, 'Você não tem permissão para adicionar informações.')
        return redirect('/informacoes/lista/')
    if request.method == 'POST':
        form = InformacoesForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False)
            c.empresa = request.user.empresa
            c.save()
            registrar_log(
                request, "CRIAR", "Informações", c.descricao,
                f"Adicionou a informação: {c.codigo} - {c.descricao}",
                c.id, gerar_alteracoes(obj_novo=c)
            )
            messages.success(request, 'Informações adicionada com sucesso!')
            cid = str(c.codigo)
            return redirect('/informacoes/lista/?tp=cod&s=' + cid)
        else:
            error_messages = []
            for field in form:
                if field.errors: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'informacoes/add.html', {'form': form, 'error_messages': error_messages})
    else: form = InformacoesForm()
    return render(request, 'informacoes/add.html', {'form': form})

@login_required
def att_informacao(request, codigo):
    c = get_object_or_404(Informacoes, codigo=codigo, empresa=request.user.empresa)
    it_old = Informacoes.objects.get(codigo=c.codigo, empresa=request.user.empresa)
    form = InformacoesForm(instance=c)
    if not request.user.has_perm('informacoes.change_informacoes'):
        messages.info(request, 'Você não tem permissão para editar informações.')
        return redirect('/informacoes/lista/')
    if request.method == 'POST':
        form = InformacoesForm(request.POST, instance=c)
        if form.is_valid():
            c.save()
            registrar_log(
                request, "ALTERAR", "Informações", c.descricao,
                f"Alterou a informação: {c.codigo} - {c.descricao}",
                c.id, gerar_alteracoes(it_old, c)
            )
            next_url = request.POST.get('next') or request.GET.get('next')
            cid = str(c.codigo)
            messages.success(request, 'Informações atualizada com sucesso!')
            if next_url: return redirect(next_url)
            else: return redirect('/informacoes/lista/?tp=cod&s=' + cid)
        else:
            error_messages = []
            for field in form:
                if field.errors: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'informacoes/att.html', {'form': form, 'c': c, 'error_messages': error_messages})
    else: return render(request, 'informacoes/att.html', {'form': form, 'c': c})

@login_required
def del_informacao(request, codigo):
    if not request.user.has_perm('informacoes.delete_informacoes'):
        messages.info(request, 'Você não tem permissão para deletar informacoes.')
        return redirect('/informacoes/lista/')
    c = get_object_or_404(Informacoes, codigo=codigo, empresa=request.user.empresa)
    registrar_log(
        request, "EXCLUIR", "Informações", c.descricao,
        f"Excluiu a informação: {c.codigo} - {c.descricao}",
        c.id, gerar_alteracoes(obj_antigo=c)
    )
    c.delete()
    messages.success(request, 'Informações deletada com sucesso!')
    return redirect('/informacoes/lista/')