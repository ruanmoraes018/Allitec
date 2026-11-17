from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Estoque
from .forms import EstoqueForm
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

@verifica_permissao('estoques.view_estoque')
@login_required
def lista_estoques(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')
    empresa = request.user.empresa
    estoques = Estoque.objects.filter(empresa=empresa)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        estoques = estoques.filter(descricao__icontains=norm_s).order_by('descricao')
    elif tp == 'cod' and s:
        try: estoques = estoques.filter(codigo__iexact=s).order_by('descricao')
        except ValueError: estoques = Estoque.objects.none()
    if reg == 'todos': num_pagina = estoques.count() or 1
    else:
        try: num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError: num_pagina = 10  # Valor padrão
    paginator = Paginator(estoques, num_pagina)
    page = request.GET.get('page')
    estoques = paginator.get_page(page)
    return render(request, 'estoques/lista.html', {'estoques': estoques, 's': s, 'tp': tp, 'reg': reg,})

@login_required
def lista_estoques_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit(): condicao_busca = Q(descricao__icontains=termo_busca) | Q(codigo=termo_busca)
        else: condicao_busca = Q(descricao__icontains=termo_busca)
        estoques = Estoque.objects.filter(condicao_busca & Q(empresa=empresa))[:20]
        results = [{'id': estoque.codigo, 'text': f"{estoque.descricao.upper()}"} for estoque in estoques]
        return JsonResponse({'results': results})
    except Exception as e:
        return JsonResponse({'results': [], 'error': str(e)})

@login_required
def add_estoque(request):
    error_messages = []
    if not request.user.has_perm('estoques.add_estoque'):
        messages.info(request, 'Você não tem permissão para adicionar estoques.')
        return redirect('/estoques/lista/')
    empresa = request.user.empresa
    if request.method != 'POST':
        form = EstoqueForm(empresa=empresa, user=request.user)
        return render(request, 'estoques/add.html', {'form': form, 'error_messages': error_messages})
    form = EstoqueForm(request.POST, empresa=empresa, user=request.user)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'estoques/add.html', {'form': form, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            c = form.save(commit=False)
            c.empresa = empresa
            c.save()
            registrar_log(request, "CRIAR", "Estoque", c.descricao, f"Adicionou o estoque: {c.codigo} - {c.descricao}", c.id, gerar_alteracoes(obj_novo=c))
            messages.success(request, 'Estoque adicionado com sucesso!')
            cid = str(c.codigo)
            return redirect('/estoques/lista/?tp=cod&s=' + cid)
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
    return render(request, 'estoques/add.html', {'form': form, 'error_messages': error_messages})

@login_required
def att_estoque(request, codigo):
    error_messages = []
    empresa = request.user.empresa
    if not request.user.has_perm('estoques.change_estoque'):
        messages.info(request, 'Você não tem permissão para editar estoques.')
        return redirect('/estoques/lista/')
    c = get_object_or_404(Estoque, codigo=codigo, empresa=empresa)
    # Guarda o estado antigo para o log
    it_old = Estoque.objects.get(pk=c.pk, empresa=empresa)
    if request.method != 'POST':
        form = EstoqueForm(instance=c, empresa=empresa, user=request.user)
        return render(request, 'estoques/att.html', {'form': form, 'c': c, 'error_messages': error_messages})
    form = EstoqueForm(request.POST, instance=c, empresa=empresa, user=request.user)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'estoques/att.html', {'form': form, 'c': c, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            c = form.save()
            registrar_log(request, "ALTERAR", "Estoque", c.descricao, f"Alterou o estoque: {c.codigo} - {c.descricao}", c.id, gerar_alteracoes(it_old, c))
            next_url = (request.POST.get('next') or request.GET.get('next'))
            cid = str(c.codigo)
            messages.success(request, 'Estoque atualizado com sucesso!')
            if next_url:
                return redirect(next_url)
            return redirect('/estoques/lista/?tp=cod&s=' + cid)
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
    return render(request, 'estoques/att.html', {'form': form, 'c': c, 'error_messages': error_messages})

@login_required
def del_estoque(request, codigo):
    if not request.user.has_perm('estoques.delete_estoque'):
        messages.info(request, 'Você não tem permissão para deletar estoques.')
        return redirect('/estoques/lista/')
    try:
        with transaction.atomic():
            c = get_object_or_404(Estoque, codigo=codigo, empresa=request.user.empresa)
            registrar_log(request, "EXCLUIR", "Estoque", c.descricao, f"Excluiu o estoque: {c.codigo} - {c.descricao}", c.id, gerar_alteracoes(obj_antigo=c))
            c.delete()
            messages.success(request, 'Estoque deletado com sucesso!')
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
    return redirect('/estoques/lista/')