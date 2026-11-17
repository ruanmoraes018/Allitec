from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Grupo
from .forms import GrupoForm
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

@verifica_permissao('grupos.view_grupo')
@login_required
def lista_grupos(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')
    empresa = request.user.empresa
    grupos = Grupo.objects.filter(vinc_emp=empresa)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        grupos = grupos.filter(nome_grupo__icontains=norm_s).order_by('nome_grupo')
    elif tp == 'cod' and s:
        try: grupos = grupos.filter(codigo__iexact=s).order_by('nome_grupo')
        except ValueError: grupos = Grupo.objects.none()
    if reg == 'todos': num_pagina = grupos.count() or 1
    else:
        try: num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError: num_pagina = 10  # Valor padrão
    paginator = Paginator(grupos, num_pagina)
    page = request.GET.get('page')
    grupos = paginator.get_page(page)
    return render(request, 'grupos/lista.html', {'grupos': grupos, 's': s, 'tp': tp, 'reg': reg,})

@login_required
def lista_grupos_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit(): condicao_busca = Q(nome_grupo__icontains=termo_busca) | Q(codigo=termo_busca)
        else: condicao_busca = Q(nome_grupo__icontains=termo_busca)
        grupos = Grupo.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': grupo.codigo, 'text': f"{grupo.nome_grupo.upper()}"} for grupo in grupos]
        return JsonResponse({'results': results})
    except Exception as e: return JsonResponse({'results': [], 'error': str(e)})

@login_required
def add_grupo(request):
    error_messages = []
    empresa = request.user.empresa
    if not request.user.has_perm('grupos.add_grupo'):
        messages.info(request, 'Você não tem permissão para adicionar grupos.')
        return redirect('/grupos/lista/')
    if request.method != 'POST':
        form = GrupoForm()
        return render(request, 'grupos/add.html', {'form': form, 'error_messages': error_messages})
    form = GrupoForm(request.POST)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'grupos/add.html', {'form': form, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            nome = form.cleaned_data['nome_grupo'].strip().upper()
            # Verifica duplicata antes de salvar
            if Grupo.objects.filter(nome_grupo=nome, vinc_emp=empresa).exists():
                messages.warning(request, f'O grupo "{nome}" já está cadastrado.')
                return render(request, 'grupos/add.html', {'form': form})
            b = form.save(commit=False)
            b.nome_grupo = nome
            b.vinc_emp = empresa
            b.save()
            registrar_log(request, "CRIAR", "Grupo", b.nome_grupo, f"Adicionou o grupo: {b.codigo} - {b.nome_grupo}", b.id, gerar_alteracoes(obj_novo=b))
            messages.success(request, 'Grupo adicionado com sucesso!')
            return redirect('/grupos/lista/?tp=cod&s=' + str(b.codigo))
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
    return render(request, 'grupos/add.html', {'form': form, 'error_messages': error_messages})

@login_required
@require_POST
def add_grupo_ajax(request):
    nome = request.POST.get('nome', '').strip().upper()
    if not nome:
        return JsonResponse({'erro': 'Nome vazio'}, status=400)
    try:
        with transaction.atomic():
            empresa = request.user.empresa
            grupo, criado = Grupo.objects.get_or_create(nome_grupo=nome, vinc_emp=empresa)
            if criado:
                registrar_log(request, "CRIAR", "Grupo", grupo.nome_grupo, f"Adicionou o grupo: {grupo.codigo} - {grupo.nome_grupo}", grupo.id, gerar_alteracoes(obj_novo=grupo))
            return JsonResponse({'id': grupo.codigo, 'nome': grupo.nome_grupo, 'criado': criado})
    except ValueError as e:
        return JsonResponse({'erro': e}, status=400)
    except Exception as e:
        return JsonResponse({'erro': e}, status=400)

@login_required
def att_grupo(request, codigo):
    error_messages = []
    empresa = request.user.empresa
    g = get_object_or_404(Grupo, codigo=codigo, vinc_emp=request.user.empresa)
    if not request.user.has_perm('grupos.change_grupo'):
        messages.info(request, 'Você não tem permissão para editar grupos.')
        return redirect('/grupos/lista/')
    it_old = Grupo.objects.get(codigo=g.codigo, vinc_emp=request.user.empresa)
    if request.method != 'POST':
        form = GrupoForm(instance=g)
        return render(request, 'grupos/att.html', {'form': form, 'g': g, 'error_messages': error_messages})
    form = GrupoForm(request.POST, instance=g)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'grupos/att.html', {'form': form, 'g': g, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            nome = form.cleaned_data['nome_grupo'].strip().upper()
            empresa = request.user.empresa
            # Verifica duplicata excluindo o próprio registro
            if Grupo.objects.filter(nome_grupo=nome, vinc_emp=empresa).exclude(codigo=codigo).exists():
                messages.warning(request, f'O grupo "{nome}" já está cadastrado.')
                return render(request, 'grupos/att.html', {'form': form, 'g': g})
            form.nome_grupo = nome
            g = form.save()
            registrar_log(request, "ALTERAR", "Grupo", g.nome_grupo, f"Alterou o grupo: {g.codigo} - {g.nome_grupo}",  g.id, gerar_alteracoes(it_old, g))
            messages.success(request, 'Grupo atualizado com sucesso!')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('/grupos/lista/?tp=cod&s=' + str(g.codigo))
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
    return render(request, 'grupos/att.html', {'form': form, 'g': g, 'error_messages': error_messages})

@login_required
def del_grupo(request, codigo):
    if not request.user.has_perm('grupos.delete_grupo'):
        messages.info(request, 'Você não tem permissão para deletar grupos.')
        return redirect('/grupos/lista/')
    try:
        with transaction.atomic():
            g = get_object_or_404(Grupo, codigo=codigo, vinc_emp=request.user.empresa)
            registrar_log(request, "EXCLUIR", "Grupo", g.nome_grupo, f"Excluiu o grupo: {g.codigo} - {g.nome_grupo}", g.id, gerar_alteracoes(obj_antigo=g))
            g.delete()
            messages.success(request, 'Grupo deletado com sucesso!')
            return redirect('/grupos/lista/')
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
    return redirect('/grupos/lista/')