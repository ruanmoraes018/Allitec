from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Estado
from .forms import EstadoForm
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

@verifica_permissao('estados.view_estado')
@login_required
def lista_estados(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')
    empresa = request.user.empresa
    estados = Estado.objects.filter(vinc_emp=empresa)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        estados = estados.filter(nome_estado__icontains=norm_s).order_by('nome_estado')
    elif tp == 'cod' and s:
        try: estados = estados.filter(codigo__iexact=s).order_by('nome_estado')
        except ValueError: estados = Estado.objects.none()
    if reg == 'todos': num_pagina = estados.count() or 1
    else:
        try: num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError: num_pagina = 10  # Valor padrão
    paginator = Paginator(estados, num_pagina)
    page = request.GET.get('page')
    estados = paginator.get_page(page)
    return render(request, 'estados/lista.html', {'estados': estados, 's': s, 'tp': tp, 'reg': reg,})

@login_required
def lista_estados_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit(): condicao_busca = Q(nome_estado__icontains=termo_busca) | Q(codigo=termo_busca)
        else: condicao_busca = Q(nome_estado__icontains=termo_busca)
        estados = Estado.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': estado.codigo, 'text': f"{estado.nome_estado.upper()}"} for estado in estados]
        return JsonResponse({'results': results})
    except Exception as e:
        return JsonResponse({'results': [], 'error': str(e)})

@login_required
def add_estado(request):
    error_messages = []
    if not request.user.has_perm('estados.add_estado'):
        messages.info(request, 'Você não tem permissão para adicionar estados.')
        return redirect('/estados/lista/')
    empresa = request.user.empresa
    if request.method != 'POST':
        form = EstadoForm()
        return render(request, 'estados/add.html', {'form': form, 'error_messages': error_messages})
    form = EstadoForm(request.POST)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'estados/add.html', {'form': form, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            e = form.save(commit=False)
            e.vinc_emp = empresa
            e.save()
            registrar_log(request, "CRIAR", "Estado", e.nome_estado, f"Adicionou o estado: {e.codigo} - {e.nome_estado}", e.id, gerar_alteracoes(obj_novo=e))
            messages.success(request, 'Estado adicionado com sucesso!')
            est = str(e.codigo)
            return redirect('/estados/lista/?tp=cod&s=' + est)
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
    return render(request, 'estados/add.html', {'form': form, 'error_messages': error_messages})

@login_required
def att_estado(request, codigo):
    error_messages = []
    e = get_object_or_404(Estado, codigo=codigo, vinc_emp=request.user.empresa)
    it_old = Estado.objects.get(codigo=e.codigo, vinc_emp=request.user.empresa)
    if not request.user.has_perm('estados.change_estado'):
        messages.info(request, 'Você não tem permissão para editar estados.')
        return redirect('/estados/lista/')
    if request.method != 'POST':
        form = EstadoForm(instance=e)
        return render(request, 'estados/att.html', {'form': form, 'e': e, 'error_messages': error_messages})
    form = EstadoForm(request.POST, instance=e)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'estados/att.html', {'form': form, 'e': e, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            e = form.save()
            registrar_log(
                request, "ALTERAR", "Estado", e.nome_estado,
                f"Alterou o estado: {e.codigo} - {e.nome_estado}",
                e.id, gerar_alteracoes(it_old, e)
            )
            next_url = request.POST.get('next') or request.GET.get('next')
            est = str(e.codigo)
            messages.success(request, 'Estado atualizado com sucesso!')
            if next_url: return redirect(next_url)
            else: return redirect('/estados/lista/?tp=cod&s=' + est)
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
    return render(request, 'estados/att.html', {'form': form, 'e': e, 'error_messages': error_messages})

@login_required
def del_estado(request, codigo):
    if not request.user.has_perm('estados.delete_estado'):
        messages.info(request, 'Você não tem permissão para deletar estados.')
        return redirect('/estados/lista/')
    try:
        with transaction.atomic():
            e = get_object_or_404(Estado, codigo=codigo, vinc_emp=request.user.empresa)
            registrar_log(
                request, "EXCLUIR", "Estado", e.nome_estado,
                f"Excluiu o estado: {e.codigo} - {e.nome_estado}",
                e.id, gerar_alteracoes(obj_antigo=e)
            )
            e.delete()
            messages.success(request, 'Estado deletado com sucesso!')
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
    return redirect('/estados/lista/')