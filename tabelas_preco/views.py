from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import TabelaPreco
from .forms import TabelaPrecoForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from django.db.models import Q
from util.logs import gerar_alteracoes, registrar_log
from django.db import DatabaseError, IntegrityError, transaction
from django.core.exceptions import ObjectDoesNotExist

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('tabelas_preco.view_tabelapreco')
@login_required
def lista_tabelas_preco(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')
    empresa = request.user.empresa
    tabelas_preco = TabelaPreco.objects.filter(vinc_emp=empresa)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        tabelas_preco = tabelas_preco.filter(descricao__icontains=norm_s).order_by('descricao')
    elif tp == 'cod' and s:
        try: tabelas_preco = tabelas_preco.filter(codigo__iexact=s).order_by('descricao')
        except ValueError: tabelas_preco = TabelaPreco.objects.none()
    if reg == 'todos': num_pagina = tabelas_preco.count() or 1
    else:
        try: num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError: num_pagina = 10  # Valor padrão
    paginator = Paginator(tabelas_preco, num_pagina)
    page = request.GET.get('page')
    tabelas_preco = paginator.get_page(page)
    return render(request, 'tabelas_preco/lista.html', {'tabelas_preco': tabelas_preco, 's': s, 'tp': tp, 'reg': reg,})

@login_required
def lista_tabelas_preco_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit(): condicao_busca = Q(descricao__icontains=termo_busca) | Q(codigo=termo_busca)
        else: condicao_busca = Q(descricao__icontains=termo_busca)
        tabelas_preco = TabelaPreco.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': tabela_preco.codigo, 'text': f"{tabela_preco.descricao.upper()}"} for tabela_preco in tabelas_preco]
        return JsonResponse({'results': results})
    except Exception as e: return JsonResponse({'results': [], 'error': str(e)})

@login_required
def get_tabela_preco(request):
    tabela_id = request.GET.get("id")
    try:
        tabela = TabelaPreco.objects.get(codigo=tabela_id, vinc_emp=request.user.empresa)
        return JsonResponse({"id": tabela.codigo, "descricao": tabela.descricao, "margem": tabela.margem})
    except TabelaPreco.DoesNotExist: return JsonResponse({"error": "Tabela não encontrada"}, status=404)

@login_required
def add_tabelas_preco(request):
    error_messages = []
    empresa = request.user.empresa
    if not request.user.has_perm('tabelas_preco.add_tabelapreco'):
        messages.info(request, 'Você não tem permissão para adicionar tabelas de preço.')
        return redirect('/tabelas_preco/lista/')
    if request.method != 'POST':
        form = TabelaPrecoForm()
        return render(request, 'tabelas_preco/add.html', {'form': form, 'error_messages': error_messages})
    form = TabelaPrecoForm(request.POST)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'tabelas_preco/add.html', {'form': form, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            c = form.save(commit=False)
            c.vinc_emp = empresa
            c.save()
            registrar_log(
                request, "CRIAR", "Tabela de Preço", c.descricao,
                f"Adicionou a tabela de preço: {c.codigo} - {c.descricao}",
                c.id, gerar_alteracoes(obj_novo=c)
            )
            messages.success(request, 'Tabela de Preço adicionada com sucesso!')
            cid = str(c.codigo)
            return redirect('/tabelas_preco/lista/?tp=cod&s=' + cid)
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
    return render(request, 'tabelas_preco/add.html', {'form': form, 'error_messages': error_messages})

@login_required
def att_tabelas_preco(request, codigo):
    error_messages = []
    c = get_object_or_404(TabelaPreco, codigo=codigo, vinc_emp=request.user.empresa)
    it_old = TabelaPreco.objects.get(codigo=c.codigo, vinc_emp=request.user.empresa)
    if not request.user.has_perm('tabelas_preco.change_tabelapreco'):
        messages.info(request, 'Você não tem permissão para editar tabelas de preço.')
        return redirect('/tabelas_preco/lista/')
    if request.method != 'POST':
        form = TabelaPrecoForm(instance=c)
        return render(request, 'tabelas_preco/att.html', {'form': form, 'c': c, 'error_messages': error_messages})
    form = TabelaPrecoForm(request.POST, instance=c)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'tabelas_preco/att.html', {'form': form, 'c': c, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            c = form.save(commit=False)
            c.save()
            registrar_log(
                request, "ALTERAR", "Tabela de Preço", c.descricao,
                f"Alterou a tabela de preço: {c.codigo} - {c.descricao}",
                c.id, gerar_alteracoes(it_old, c)
            )
            cid = str(c.codigo)
            messages.success(request, 'Tabela de Preço atualizada com sucesso!')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url: return redirect(next_url)
            else: return redirect('/tabelas_preco/lista/?tp=cod&s=' + cid)
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
    return render(request, 'tabelas_preco/att.html', {'form': form, 'c': c, 'error_messages': error_messages})

@login_required
def del_tabelas_preco(request, codigo):
    if not request.user.has_perm('tabelas_preco.delete_tabelapreco'):
        messages.info(request, 'Você não tem permissão para deletar tabelas de preço.')
        return redirect('/tabelas_preco/lista/')
    try:
        with transaction.atomic():
            c = get_object_or_404(TabelaPreco, codigo=codigo, vinc_emp=request.user.empresa)
            registrar_log(
                request, "EXCLUIR", "Tabela de Preço", c.descricao,
                f"Excluiu a tabela de preço: {c.codigo} - {c.descricao}",
                c.id, gerar_alteracoes(obj_antigo=c)
            )
            c.delete()
            messages.success(request, 'Tabela de Preço deletada com sucesso!')
            return redirect('/tabelas_preco/lista/')
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
    return redirect('/tabelas_preco/lista/')