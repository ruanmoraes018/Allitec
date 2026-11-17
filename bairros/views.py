from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from util.logs import gerar_alteracoes, registrar_log
from .models import Bairro
from .forms import BairroForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.db import DatabaseError, IntegrityError, transaction

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('bairros.view_bairro')
@login_required
def lista_bairros(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')
    empresa = request.user.empresa
    bairros = Bairro.objects.filter(vinc_emp=empresa)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        bairros = bairros.filter(nome_bairro__icontains=norm_s).order_by('nome_bairro')
    elif tp == 'cod' and s:
        try: bairros = bairros.filter(codigo__iexact=s).order_by('nome_bairro')
        except ValueError: bairros = Bairro.objects.none()
    if reg == 'todos': num_pagina = bairros.count() or 1
    else:
        try: num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError: num_pagina = 10  # Valor padrão
    paginator = Paginator(bairros, num_pagina)
    page = request.GET.get('page')
    bairros = paginator.get_page(page)
    return render(request, 'bairros/lista.html', {'bairros': bairros, 's': s, 'tp': tp, 'reg': reg,})

@login_required
def lista_bairros_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit(): condicao_busca = Q(nome_bairro__icontains=termo_busca) | Q(codigo=termo_busca)
        else: condicao_busca = Q(nome_bairro__icontains=termo_busca)
        bairros = Bairro.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': bairro.codigo, 'text': f"{bairro.nome_bairro.upper()}"} for bairro in bairros]
        return JsonResponse({'results': results})
    except Exception as e:
        return JsonResponse({'results': [], 'error': str(e)})

@login_required
def add_bairro(request):
    error_messages = []
    empresa = request.user.empresa
    if not request.user.has_perm('bairros.add_bairro'):
        messages.info(request, 'Você não tem permissão para adicionar bairros.')
        return redirect('/bairros/lista/')
    if request.method != 'POST':
        form = BairroForm()
        return render(request, 'bairros/add.html', {'form': form, 'error_messages': error_messages})
    form = BairroForm(request.POST)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'bairros/add.html', {'form': form, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            nome = form.cleaned_data['nome_bairro'].strip().upper()
            # Verifica duplicata antes de salvar
            if Bairro.objects.filter(nome_bairro=nome, vinc_emp=empresa).exists():
                messages.warning(request, f'O bairro "{nome}" já está cadastrado.')
                return render(request, 'bairros/add.html', {'form': form})
            b = form.save(commit=False)
            b.nome_bairro = nome
            b.vinc_emp = empresa
            b.save()
            registrar_log(request, "CRIAR", "Bairro", b.nome_bairro, f"Adicionou o bairro: {b.codigo} - {b.nome_bairro}", b.id, gerar_alteracoes(obj_novo=b))
            messages.success(request, 'Bairro adicionado com sucesso!')
            return redirect('/bairros/lista/?tp=cod&s=' + str(b.codigo))
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
    return render(request, 'bairros/add.html', {'form': form, 'error_messages': error_messages})

@login_required
@require_POST
def add_bairro_ajax(request):
    nome = request.POST.get('nome', '').strip().upper()
    if not nome:
        return JsonResponse({'erro': 'Nome vazio'}, status=400)
    try:
        with transaction.atomic():
            empresa = request.user.empresa
            bairro, criado = Bairro.objects.get_or_create(nome_bairro=nome, vinc_emp=empresa)
            if criado:
                registrar_log(request, "CRIAR", "Bairro", bairro.nome_bairro, f"Adicionou o bairro: {bairro.codigo} - {bairro.nome_bairro}", bairro.id, gerar_alteracoes(obj_novo=bairro))
            return JsonResponse({'id': bairro.codigo, 'nome': bairro.nome_bairro, 'criado': criado})
    except ValueError as e:
        return JsonResponse({'erro': e}, status=400)
    except Exception as e:
        return JsonResponse({'erro': e}, status=400)

@login_required
def att_bairro(request, codigo):
    error_messages = []
    empresa = request.user.empresa
    b = get_object_or_404(Bairro, codigo=codigo, vinc_emp=empresa)
    if not request.user.has_perm('bairros.change_bairro'):
        messages.info(request, 'Você não tem permissão para editar bairros.')
        return redirect('/bairros/lista/')
    it_old = Bairro.objects.get(codigo=b.codigo, vinc_emp=empresa)
    if request.method != 'POST':
        form = BairroForm(instance=b)
        return render(request, 'bairros/att.html', {'form': form, 'b': b, 'error_messages': error_messages})
    form = BairroForm(request.POST, instance=b)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'bairros/att.html', {'form': form, 'b': b, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            nome = form.cleaned_data['nome_bairro'].strip().upper()
            empresa = request.user.empresa
            # Verifica duplicata excluindo o próprio registro
            if Bairro.objects.filter(nome_bairro=nome, vinc_emp=empresa).exclude(codigo=codigo).exists():
                messages.warning(request, f'O bairro "{nome}" já está cadastrado.')
                return render(request, 'bairros/att.html', {'form': form, 'b': b})
            form.nome_bairro = nome
            b = form.save()
            registrar_log(request, "ALTERAR", "Bairro", b.nome_bairro, f"Alterou o bairro: {b.codigo} - {b.nome_bairro}",  b.id, gerar_alteracoes(it_old, b))
            messages.success(request, 'Bairro atualizado com sucesso!')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('/bairros/lista/?tp=cod&s=' + str(b.codigo))
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
    return render(request, 'bairros/att.html', {'form': form, 'b': b, 'error_messages': error_messages})

@login_required
def del_bairro(request, codigo):
    if not request.user.has_perm('bairros.delete_bairro'):
        messages.info(request, 'Você não tem permissão para deletar bairros.')
        return redirect('/bairros/lista/')
    try:
        with transaction.atomic():
            b = get_object_or_404(Bairro, codigo=codigo, vinc_emp=request.user.empresa)
            registrar_log(request, "EXCLUIR", "Bairro", b.nome_bairro, f"Excluiu o bairro: {b.codigo} - {b.nome_bairro}", b.id, gerar_alteracoes(obj_antigo=b))
            b.delete()
            messages.success(request, 'Bairro deletado com sucesso!')
            return redirect('/bairros/lista/')
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
    return redirect('/bairros/lista/')