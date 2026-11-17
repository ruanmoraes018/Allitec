from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Cidade
from .forms import CidadeForm
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

@verifica_permissao('cidades.view_cidade')
@login_required
def lista_cidades(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')
    empresa = request.user.empresa
    cidades = Cidade.objects.filter(vinc_emp=empresa)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        cidades = cidades.filter(nome_cidade__icontains=norm_s).order_by('nome_cidade')
    elif tp == 'cod' and s:
        try: cidades = cidades.filter(codigo__iexact=s).order_by('nome_cidade')
        except ValueError: cidades = Cidade.objects.none()
    if reg == 'todos': num_pagina = cidades.count() or 1
    else:
        try: num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError: num_pagina = 10  # Valor padrão
    paginator = Paginator(cidades, num_pagina)
    page = request.GET.get('page')
    cidades = paginator.get_page(page)
    return render(request, 'cidades/lista.html', {'cidades': cidades, 's': s, 'tp': tp, 'reg': reg,})

@login_required
def lista_cidades_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit(): condicao_busca = Q(nome_cidade__icontains=termo_busca) | Q(codigo=termo_busca)
        else: condicao_busca = Q(nome_cidade__icontains=termo_busca)
        cidades = Cidade.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': cidade.codigo, 'text': f"{cidade.nome_cidade.upper()}"} for cidade in cidades]
        return JsonResponse({'results': results})
    except Exception as e:
        return JsonResponse({'results': [], 'error': str(e)})

@login_required
def add_cidade(request):
    error_messages = []
    if not request.user.has_perm('cidades.add_cidade'):
        messages.info(request, 'Você não tem permissão para adicionar cidades.')
        return redirect('/cidades/lista/')
    empresa = request.user.empresa
    if request.method != 'POST':
        form = CidadeForm()
        return render(request, 'cidades/add.html', {'form': form, 'error_messages': error_messages})
    form = CidadeForm(request.POST)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'cidades/add.html', {'form': form, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            c = form.save(commit=False)
            c.vinc_emp = empresa
            c.save()
            registrar_log(request, "CRIAR", "Cidade", c.nome_cidade, f"Adicionou a cidade: {c.codigo} - {c.nome_cidade}", c.id, gerar_alteracoes(obj_novo=c))
            messages.success(request, 'Cidade adicionada com sucesso!')
            cid = str(c.codigo)
            return redirect('/cidades/lista/?tp=cod&s=' + cid)
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
    return render(request, 'cidades/add.html', {'form': form, 'error_messages': error_messages})

@login_required
def att_cidade(request, codigo):
    error_messages = []
    c = get_object_or_404(Cidade, codigo=codigo, vinc_emp=request.user.empresa)
    it_old = Cidade.objects.get(codigo=c.codigo, vinc_emp=request.user.empresa)
    if not request.user.has_perm('cidades.change_cidade'):
        messages.info(request, 'Você não tem permissão para editar cidades.')
        return redirect('/cidades/lista/')
    if request.method != 'POST':
        form = CidadeForm(instance=c)
        return render(request, 'cidades/att.html', {'form': form, 'c': c, 'error_messages': error_messages})
    form = CidadeForm(request.POST, instance=c)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'cidades/att.html', {'form': form, 'c': c, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            c = form.save()
            registrar_log(request, "ALTERAR", "Cidade", c.nome_cidade,f"Alterou a cidade: {c.codigo} - {c.nome_cidade}", c.id, gerar_alteracoes(it_old, c))
            next_url = request.POST.get('next') or request.GET.get('next')
            cid = str(c.codigo)
            messages.success(request, 'Cidade atualizada com sucesso!')
            if next_url: return redirect(next_url)
            else: return redirect('/cidades/lista/?tp=cod&s=' + cid)
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
    return render(request, 'cidades/att.html', {'form': form, 'c': c, 'error_messages': error_messages})

@login_required
def del_cidade(request, codigo):
    if not request.user.has_perm('cidades.delete_cidade'):
        messages.info(request, 'Você não tem permissão para deletar cidades.')
        return redirect('/cidades/lista/')
    try:
        with transaction.atomic():
            c = get_object_or_404(Cidade, codigo=codigo, vinc_emp=request.user.empresa)
            registrar_log(request, "EXCLUIR", "Cidade", c.nome_cidade, f"Excluiu a cidade: {c.codigo} - {c.nome_cidade}", c.id, gerar_alteracoes(obj_antigo=c))
            c.delete()
            messages.success(request, 'Cidade deletada com sucesso!')
            return redirect('/cidades/lista/')
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
    return redirect('/cidades/lista/')