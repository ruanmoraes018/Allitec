from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Banco
from .forms import BancoForm
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

@verifica_permissao('bancos.view_banco')
@login_required
def lista_bancos(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')
    empresa = request.user.empresa
    bancos = Banco.objects.filter(vinc_emp=empresa)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        bancos = bancos.filter(banco_normalizado__icontains=norm_s).order_by('nome_banco')
    elif tp == 'cod' and s:
        try: bancos = bancos.filter(codigo__iexact=s).order_by('nome_banco')
        except ValueError: bancos = Banco.objects.none()
    if reg == 'todos': num_pagina = bancos.count() or 1
    else:
        try: num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError: num_pagina = 10  # Valor padrão
    paginator = Paginator(bancos, num_pagina)
    page = request.GET.get('page')
    bancos = paginator.get_page(page)
    return render(request, 'bancos/lista.html', {'bancos': bancos, 's': s, 'tp': tp, 'reg': reg,})

@login_required
def lista_bancos_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit(): condicao_busca = Q(nome_banco__icontains=termo_busca) | Q(codigo=termo_busca)
        else: condicao_busca = Q(nome_banco__icontains=termo_busca)
        bancos = Banco.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': banco.codigo, 'text': f"{banco.codigo} - {banco.nome_banco.upper()}"} for banco in bancos]
        return JsonResponse({'results': results})
    except Exception as e:
        return JsonResponse({'results': [], 'error': str(e)})

@login_required
def add_banco(request):
    error_messages = []
    if not request.user.has_perm('bancos.add_banco'):
        messages.info(request, 'Você não tem permissão para adicionar bancos.')
        return redirect('/bancos/lista/')
    empresa = request.user.empresa
    if request.method != 'POST':
        form = BancoForm()
        return render(request, 'bancos/add.html', {'form': form, 'error_messages': error_messages})
    form = BancoForm(request.POST)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'bancos/add.html', {'form': form, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            b = form.save(commit=False)
            b.vinc_emp = empresa
            b.save()
            registrar_log(request, "CRIAR", "Banco", b.nome_banco,f"Adicionou o banco: {b.codigo} - {b.nome_banco}",b.id, gerar_alteracoes(obj_novo=b))
            messages.success(request, 'Banco adicionado com sucesso!')
            bank = str(b.codigo)
            return redirect('/bancos/lista/?tp=cod&s=' + bank)
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
    return render(request, 'bancos/add.html', {'form': form, 'error_messages': error_messages})

@login_required
def att_banco(request, codigo):
    error_messages = []
    b = get_object_or_404(Banco, codigo=codigo, vinc_emp=request.user.empresa)
    it_old = Banco.objects.get(codigo=b.codigo, vinc_emp=request.user.empresa)
    if not request.user.has_perm('bancos.change_banco'):
        messages.info(request, 'Você não tem permissão para editar bancos.')
        return redirect('/bancos/lista/')
    if request.method != 'POST':
        form = BancoForm(instance=b)
        return render(request, 'bancos/att.html', {'form': form, 'b': b, 'error_messages': error_messages})
    form = BancoForm(request.POST, instance=b)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'bancos/att.html', {'form': form, 'b': b, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            b = form.save()
            registrar_log(request, "ALTERAR", "Banco", b.nome_banco,f"Alterou o banco: {b.codigo} - {b.nome_banco}",b.id, gerar_alteracoes(it_old, b))
            next_url = request.POST.get('next') or request.GET.get('next')
            bank = str(b.codigo)
            messages.success(request, 'Banco atualizado com sucesso!')
            if next_url: return redirect(next_url)
            else: return redirect('/bancos/lista/?tp=cod&s=' + bank)
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
    return render(request, 'bancos/att.html', {'form': form, 'b': b, 'error_messages': error_messages})

@login_required
def del_banco(request, codigo):
    if not request.user.has_perm('bancos.delete_banco'):
        messages.info(request, 'Você não tem permissão para deletar bancos.')
        return redirect('/bancos/lista/')
    try:
        with transaction.atomic():
            b = get_object_or_404(Banco, codigo=codigo, vinc_emp=request.user.empresa)
            registrar_log(request, "EXCLUIR", "Banco", b.nome_banco,f"Excluiu o banco: {b.codigo} - {b.nome_banco}",b.id, gerar_alteracoes(obj_antigo=b))
            b.delete()
            messages.success(request, 'Banco deletado com sucesso!')
            return redirect('/bancos/lista/')
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
    return redirect('/bancos/lista/')