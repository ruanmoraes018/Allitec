from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import GrupoRegraProduto
from .forms import GrupoRegraProdutoForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from filiais.models import Usuario
from django.views.decorators.http import require_POST
from django.db.models import Q
from util.logs import gerar_alteracoes, registrar_log

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('regras_produto.view_gruporegraproduto')
@login_required
def lista_grupos_regras(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')
    empresa = request.user.empresa
    grupos_regras = GrupoRegraProduto.objects.filter(vinc_emp=empresa)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        grupos_regras = grupos_regras.filter(descricao__icontains=norm_s).order_by('descricao')
    elif tp == 'cod' and s:
        try: grupos_regras = grupos_regras.filter(cod_local__iexact=s).order_by('descricao')
        except ValueError: grupos_regras = GrupoRegraProduto.objects.none()
    if reg == 'todos': num_pagina = grupos_regras.count() or 1
    else:
        try: num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError: num_pagina = 10  # Valor padrão
    paginator = Paginator(grupos_regras, num_pagina)
    page = request.GET.get('page')
    grupos_regras = paginator.get_page(page)
    return render(request, 'grupo_regras/lista.html', {'grupos_regras': grupos_regras, 's': s, 'tp': tp, 'reg': reg,})

@login_required
def lista_grupos_regras_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit(): condicao_busca = Q(descricao__icontains=termo_busca) | Q(cod_local=termo_busca)
        else: condicao_busca = Q(descricao__icontains=termo_busca)
        grupos_regras = GrupoRegraProduto.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': grupo.cod_local, 'text': f"{grupo.descricao.upper()}"} for grupo in grupos_regras]
        return JsonResponse({'results': results})
    except Exception as e: return JsonResponse({'results': [], 'error': str(e)})

@login_required
def add_grupo_regras(request):
    if not request.user.has_perm('regras_produto.add_gruporegraproduto'):
        messages.info(request, 'Você não tem permissão para adicionar grupos de regras.')
        return redirect('/grupos_regras/lista/')
    if request.method == 'POST':
        form = GrupoRegraProdutoForm(request.POST)
        if form.is_valid():
            g = form.save(commit=False)
            g.vinc_emp = request.user.empresa
            g.save()
            registrar_log(
                request, "CRIAR", "Grupo de Regras", g.descricao,
                f"Adicionou o grupo de regras: {g.cod_local} - {g.descricao}",
                g.id, gerar_alteracoes(obj_novo=g)
            )
            messages.success(request, 'Grupo de Regras adicionado com sucesso!')
            gp = str(g.cod_local)
            return redirect('/grupo_regras/lista/?tp=cod&s=' + gp)
        else:
            error_messages = []
            for field in form:
                if field.errors: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'grupo_regras/add.html', {'form': form, 'error_messages': error_messages})
    else: form = GrupoRegraProdutoForm()
    return render(request, 'grupo_regras/add.html', {'form': form})

@login_required
def att_grupo_regras(request, cod_local):
    g = get_object_or_404(GrupoRegraProduto, cod_local=cod_local, vinc_emp=request.user.empresa)
    it_old = GrupoRegraProduto.objects.get(cod_local=g.cod_local, vinc_emp=request.user.empresa)
    form = GrupoRegraProdutoForm(instance=g)
    if not request.user.has_perm('regras_produto.change_gruporegraproduto'):
        messages.info(request, 'Você não tem permissão para editar grupos de regras.')
        return redirect('/grupo_regras/lista/')
    if request.method == 'POST':
        form = GrupoRegraProdutoForm(request.POST, instance=g)
        if form.is_valid():
            g.save()
            registrar_log(
                request, "ALTERAR", "Grupo de Regras", g.descricao,
                f"Alterou o grupo de regras: {g.cod_local} - {g.descricao}",
                g.id, gerar_alteracoes(it_old, g)
            )
            next_url = request.POST.get('next') or request.GET.get('next')
            gp = str(g.cod_local)
            messages.success(request, 'Grupo de Regras atualizado com sucesso!')
            if next_url: return redirect(next_url)
            else: return redirect('/grupo_regras/lista/?tp=cod&s=' + gp)
        else:
            error_messages = []
            for field in form:
                if field.errors: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'grupo_regras/att.html', {'form': form, 'g': g, 'error_messages': error_messages})
    else: return render(request, 'grupo_regras/att.html', {'form': form, 'g': g})

@login_required
def del_grupo_regras(request, cod_local):
    if not request.user.has_perm('regras_produto.delete_gruporegraproduto'):
        messages.info(request, 'Você não tem permissão para deletar grupos de regras.')
        return redirect('/grupo_regras/lista/')
    g = get_object_or_404(GrupoRegraProduto, cod_local=cod_local, vinc_emp=request.user.empresa)
    registrar_log(
        request, "EXCLUIR", "Grupo de Regras", g.descricao,
        f"Excluiu o grupo de regras: {g.cod_local} - {g.descricao}",
        g.id, gerar_alteracoes(obj_antigo=g)
    )
    g.delete()
    messages.success(request, 'Grupo de Regras deletado com sucesso!')
    return redirect('/grupo_regras/lista/')