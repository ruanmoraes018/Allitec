from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import GrupoRegraProduto
from .forms import GrupoRegraProdutoForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from util.logs import gerar_alteracoes, registrar_log
from django.db import DatabaseError, IntegrityError, transaction

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
    error_messages = []
    empresa = request.user.empresa
    if not request.user.has_perm('regras_produto.add_gruporegraproduto'):
        messages.info(request, 'Você não tem permissão para adicionar grupos de regras.')
        return redirect('/grupos_regras/lista/')
    if request.method != 'POST':
        form = GrupoRegraProdutoForm()
        return render(request, 'grupos_regras/add.html', {'form': form, 'error_messages': error_messages})
    form = GrupoRegraProdutoForm(request.POST)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'grupos_regras/add.html', {'form': form, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            g = form.save(commit=False)
            g.vinc_emp = empresa
            g.save()
            registrar_log(request, "CRIAR", "Grupo de Regras", g.descricao,f"Adicionou o grupo de regras: {g.cod_local} - {g.descricao}",g.id, gerar_alteracoes(obj_novo=g))
            messages.success(request, 'Grupo de Regras adicionado com sucesso!')
            gp = str(g.cod_local)
            return redirect('/grupo_regras/lista/?tp=cod&s=' + gp)
    except ObjectDoesNotExist:
        error_messages.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        detalhe = str(e.__cause__ if e.__cause__ else e)
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {detalhe}")
    except DatabaseError as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except ValueError as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> {str(e)}")
    except Exception as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return render(request, 'grupo_regras/add.html', {'form': form, 'error_messages': error_messages})

@login_required
def att_grupo_regras(request, cod_local):
    error_messages = []
    empresa = request.user.empresa
    g = get_object_or_404(GrupoRegraProduto, cod_local=cod_local, vinc_emp=empresa)
    it_old = GrupoRegraProduto.objects.get(cod_local=g.cod_local, vinc_emp=empresa)
    if not request.user.has_perm('regras_produto.change_gruporegraproduto'):
        messages.info(request, 'Você não tem permissão para editar grupos de regras.')
        return redirect('/grupo_regras/lista/')
    if request.method != 'POST':
        form = GrupoRegraProdutoForm(instance=g)
        return render(request, 'grupo_regras/att.html', {'form': form, 'g': g, 'error_messages': error_messages})
    form = GrupoRegraProdutoForm(request.POST, instance=g)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'grupo_regras/att.html', {'form': form, 'g': g, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            g = form.save()
            registrar_log(request, "ALTERAR", "Grupo de Regras", g.descricao,f"Alterou o grupo de regras: {g.cod_local} - {g.descricao}",g.id, gerar_alteracoes(it_old, g))
            next_url = request.POST.get('next') or request.GET.get('next')
            gp = str(g.cod_local)
            messages.success(request, 'Grupo de Regras atualizado com sucesso!')
            if next_url: return redirect(next_url)
            else: return redirect('/grupo_regras/lista/?tp=cod&s=' + gp)
    except ObjectDoesNotExist:
        error_messages.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        detalhe = str(e.__cause__ if e.__cause__ else e)
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {detalhe}")
    except DatabaseError as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except ValueError as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> {str(e)}")
    except Exception as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return render(request, 'grupo_regras/att.html', {'form': form, 'g': g, 'error_messages': error_messages})

@login_required
def del_grupo_regras(request, cod_local):
    if not request.user.has_perm('regras_produto.delete_gruporegraproduto'):
        messages.info(request, 'Você não tem permissão para deletar grupos de regras.')
        return redirect('/grupo_regras/lista/')
    try:
        with transaction.atomic():
            g = get_object_or_404(GrupoRegraProduto, cod_local=cod_local, vinc_emp=request.user.empresa)
            registrar_log(request, "EXCLUIR", "Grupo de Regras", g.descricao,f"Excluiu o grupo de regras: {g.cod_local} - {g.descricao}",g.id, gerar_alteracoes(obj_antigo=g))
            g.delete()
            messages.success(request, 'Grupo de Regras deletado com sucesso!')
            return redirect('/grupo_regras/lista/')
    except ObjectDoesNotExist:
        messages.error(request, "<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        detalhe = str(e.__cause__ if e.__cause__ else e)
        messages.error(request, f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {detalhe}")
    except DatabaseError as e:
        messages.error(request, f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except ValueError as e:
        messages.error(request, f"<i class='fa-solid fa-xmark'></i> {str(e)}")
    except Exception as e:
        messages.error(request, f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return redirect('/grupo_regras/lista/')