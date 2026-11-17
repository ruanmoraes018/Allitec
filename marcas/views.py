from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Marca
from .forms import MarcaForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.http import require_POST
from django.db.models import Q
from util.logs import gerar_alteracoes, registrar_log
from django.db import DatabaseError, IntegrityError, transaction

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('marcas.view_marca')
@login_required
def lista_marcas(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')
    empresa = request.user.empresa
    marcas = Marca.objects.filter(vinc_emp=empresa)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        marcas = marcas.filter(nome_marca__icontains=norm_s).order_by('nome_marca')
    elif tp == 'cod' and s:
        try: marcas = marcas.filter(codigo__iexact=s).order_by('nome_marca')
        except ValueError: marcas = Marca.objects.none()
    if reg == 'todos': num_pagina = marcas.count() or 1
    else:
        try: num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError: num_pagina = 10  # Valor padrão
    paginator = Paginator(marcas, num_pagina)
    page = request.GET.get('page')
    marcas = paginator.get_page(page)
    return render(request, 'marcas/lista.html', {'marcas': marcas, 's': s, 'tp': tp, 'reg': reg,})

@login_required
def lista_marcas_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit(): condicao_busca = Q(nome_marca__icontains=termo_busca) | Q(codigo=termo_busca)
        else: condicao_busca = Q(nome_marca__icontains=termo_busca)
        marcas = Marca.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': marca.codigo, 'text': f"{marca.nome_marca.upper()}"} for marca in marcas]
        return JsonResponse({'results': results})
    except Exception as e: return JsonResponse({'results': [], 'error': str(e)})

@login_required
def add_marca(request):
    error_messages = []
    empresa = request.user.empresa
    if not request.user.has_perm('marcas.add_marca'):
        messages.info(request, 'Você não tem permissão para adicionar marcas.')
        return redirect('/marcas/lista/')
    if request.method != 'POST':
        form = MarcaForm()
        return render(request, 'marcas/add.html', {'form': form, 'error_messages': error_messages})
    form = MarcaForm(request.POST)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'marcas/add.html', {'form': form, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            nome = form.cleaned_data['nome_marca'].strip().upper()
            # Verifica duplicata antes de salvar
            if Marca.objects.filter(nome_marca=nome, vinc_emp=empresa).exists():
                messages.warning(request, f'A marca "{nome}" já está cadastrada.')
                return render(request, 'marcas/add.html', {'form': form})
            b = form.save(commit=False)
            b.nome_marca = nome
            b.vinc_emp = empresa
            b.save()
            registrar_log(request, "CRIAR", "Marca", b.nome_marca, f"Adicionou a marca: {b.codigo} - {b.nome_marca}", b.id, gerar_alteracoes(obj_novo=b))
            messages.success(request, 'Marca adicionada com sucesso!')
            return redirect('/marcas/lista/?tp=cod&s=' + str(b.codigo))
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
    return render(request, 'marcas/add.html', {'form': form, 'error_messages': error_messages})

@login_required
@require_POST
def add_marca_ajax(request):
    nome = request.POST.get('nome', '').strip().upper()
    if not nome:
        return JsonResponse({'erro': 'Nome vazio'}, status=400)
    try:
        with transaction.atomic():
            empresa = request.user.empresa
            marca, criado = Marca.objects.get_or_create(nome_marca=nome, vinc_emp=empresa)
            if criado:
                registrar_log(request, "CRIAR", "Marca", marca.nome_marca, f"Adicionou a marca: {marca.codigo} - {marca.nome_marca}", marca.id, gerar_alteracoes(obj_novo=marca))
            return JsonResponse({'id': marca.codigo, 'nome': marca.nome_marca, 'criado': criado})
    except ValueError as e:
        return JsonResponse({'erro': e}, status=400)
    except Exception as e:
        return JsonResponse({'erro': e}, status=400)

@login_required
def att_marca(request, codigo):
    error_messages = []
    empresa = request.user.empresa
    b = get_object_or_404(Marca, codigo=codigo, vinc_emp=request.user.empresa)
    if not request.user.has_perm('marcas.change_marca'):
        messages.info(request, 'Você não tem permissão para editar marcas.')
        return redirect('/marcas/lista/')
    it_old = Marca.objects.get(codigo=b.codigo, vinc_emp=request.user.empresa)
    if request.method != 'POST':
        form = MarcaForm(instance=b)
        return render(request, 'marcas/att.html', {'form': form, 'b': b, 'error_messages': error_messages})
    form = MarcaForm(request.POST, instance=b)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'marcas/att.html', {'form': form, 'b': b, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            nome = form.cleaned_data['nome_marca'].strip().upper()
            # Verifica duplicata excluindo o próprio registro
            if Marca.objects.filter(nome_marca=nome, vinc_emp=empresa).exclude(codigo=codigo).exists():
                messages.warning(request, f'A marca "{nome}" já está cadastrada.')
                return render(request, 'marcas/att.html', {'form': form, 'b': b})
            form.nome_marca = nome
            b = form.save()
            registrar_log(request, "ALTERAR", "Marca", b.nome_marca, f"Alterou a marca: {b.codigo} - {b.nome_marca}",  b.id, gerar_alteracoes(it_old, b))
            messages.success(request, 'Marca atualizada com sucesso!')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('/marcas/lista/?tp=cod&s=' + str(b.codigo))
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
    return render(request, 'marcas/att.html', {'form': form, 'b': b, 'error_messages': error_messages})

@login_required
def del_marca(request, codigo):
    if not request.user.has_perm('marcas.delete_marca'):
        messages.info(request, 'Você não tem permissão para deletar marcas.')
        return redirect('/marcas/lista/')
    try:
        with transaction.atomic():
            b = get_object_or_404(Marca, codigo=codigo, vinc_emp=request.user.empresa)
            registrar_log(
                request, "EXCLUIR", "Marca", b.nome_marca,
                f"Excluiu a marca: {b.codigo} - {b.nome_marca}",
                b.id, gerar_alteracoes(obj_antigo=b)
            )
            b.delete()
            messages.success(request, 'Marca deletada com sucesso!')
            return redirect('/marcas/lista/')
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
    return redirect('/marcas/lista/')