from datetime import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Cliente
from .forms import ClienteForm
import unicodedata
from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from util.permissoes import verifica_permissao, verifica_alguma_permissao
from util.logs import gerar_alteracoes, registrar_log
from django.db import DatabaseError, IntegrityError, transaction
import copy

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('clientes.view_cliente')
@login_required
def lista_clientes(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    f_s = request.GET.get('sit')
    t_pes = request.GET.get('t_pes')
    dt_ini = request.GET.get('dt_ini')
    dt_fim = request.GET.get('dt_fim')
    p_dt = request.GET.get('p_dt')
    reg = request.GET.get('reg', '10')
    empresa = request.user.empresa
    # Lista de clientes filtrados
    clientes = Cliente.objects.filter(vinc_emp=empresa)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        clientes = clientes.filter(fantasia__icontains=norm_s).order_by('fantasia')
    elif tp == 'cod' and s:
        try: clientes = clientes.filter(codigo__iexact=s).order_by('fantasia')
        except ValueError: clientes = Cliente.objects.none()
    if p_dt == 'Sim' and dt_ini and dt_fim:
        try:
            dt_ini_dt = datetime.strptime(dt_ini, '%d/%m/%Y').date()
            dt_fim_dt = datetime.strptime(dt_fim, '%d/%m/%Y').date()
            clientes = clientes.filter(dt_reg__range=(dt_ini_dt, dt_fim_dt))
        except ValueError: clientes = Cliente.objects.none()
    if f_s in ['Ativo', 'Inativo']: clientes = clientes.filter(situacao=f_s).order_by('fantasia')
    if t_pes in ['Física', 'Jurídica']: clientes = clientes.filter(pessoa=t_pes).order_by('fantasia')
    if reg == 'todos': num_pagina = clientes.count() or 1  # Mostra todas as filials
    else:
        try: num_pagina = int(reg)
        except ValueError: num_pagina = 10
    paginator = Paginator(clientes, num_pagina)
    page = request.GET.get('page')
    clientes = paginator.get_page(page)
    return render(request, 'clientes/lista.html', {'clientes': clientes, 's': s, 'tp': tp, 't_pes': t_pes, 'dt_ini': dt_ini, 'dt_fim': dt_fim, 'p_dt': p_dt, 'reg': reg})

@login_required
def lista_clientes_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit(): condicao_busca = Q(fantasia__icontains=termo_busca) | Q(codigo=termo_busca)
        else: condicao_busca = Q(fantasia__icontains=termo_busca)
        clientes = Cliente.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{
            'id': cliente.codigo, 'text': f"{cliente.fantasia.upper()}", 'situacao': cliente.situacao, 'cpfCnpj': cliente.cpf_cnpj, 'email': cliente.email, 'tel': cliente.tel,
            'endereco': cliente.endereco, 'cep': cliente.cep, 'numero': cliente.numero, 'bairro': cliente.bairro.nome_bairro if cliente.bairro else '',
            'cidade': cliente.cidade.nome_cidade if cliente.cidade else '', 'uf': cliente.uf.nome_estado if cliente.uf else ''} for cliente in clientes]
        return JsonResponse({'results': results})
    except Exception as e:
        return JsonResponse({'results': [], 'error': str(e)})

def formatar_moeda_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def validar_limite_credito(limite_credito, vinc_fil, usuario):
    limite_filial = vinc_fil.financeiro.limite_credito_padrao
    if limite_credito > limite_filial:
        return (f"Limite de crédito ultrapassou o limite da Filial. Máximo: {formatar_moeda_br(limite_filial)}")
    if limite_credito > usuario.limite_credito:
        return (f"Limite de crédito ultrapassou o limite do seu usuário. Máximo: {formatar_moeda_br(usuario.limite_credito)}")
    return None

@login_required
def add_cliente(request):
    error_messages = []
    if not request.user.has_perm('clientes.add_cliente'):
        messages.info(request, 'Você não tem permissão para adicionar clientes.')
        return redirect('/clientes/lista/')
    empresa = request.user.empresa
    if not empresa:
        messages.error(request, 'Erro crítico: Seu usuário não está vinculado a nenhuma empresa cadastrada.')
        return redirect('/clientes/lista/')
    if request.method != 'POST':
        form = ClienteForm(empresa=empresa, user=request.user)
        return render(request, 'clientes/add.html', {'form': form, 'error_messages': error_messages})
    form = ClienteForm(data=request.POST, empresa=empresa, user=request.user)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'clientes/add.html', {'form': form, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            c = form.save(commit=False)
            c.vinc_emp = empresa
            erro_limite = validar_limite_credito(c.limite_credito, c.vinc_fil, request.user)
            if erro_limite:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> {erro_limite}")
                return render(request, 'clientes/add.html', {'form': form, 'error_messages': error_messages})
            c.save()
            registrar_log(request, "CRIAR", "Cliente", c.fantasia, f"Adicionou o cliente: {c.codigo} - {c.fantasia}", c.id, gerar_alteracoes(obj_novo=c))
            messages.success(request, 'Cliente adicionado com sucesso!')
            return redirect('/clientes/lista/?tp=cod&s=' + str(c.codigo))
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
    return render(request, 'clientes/add.html', {'form': form, 'error_messages': error_messages})


@verifica_alguma_permissao('clientes.add_cliente', 'clientes.change_cliente', 'clientes.delete_cliente')
@login_required
def att_cliente(request, codigo):
    error_messages = []
    empresa = request.user.empresa
    cli = get_object_or_404(Cliente, codigo=codigo, vinc_emp=empresa)
    it_old = copy.deepcopy(cli)  # snapshot antes de qualquer alteração
    if not request.user.has_perm('clientes.change_cliente'):
        messages.info(request, 'Você não tem permissão para editar clientes.')
        return redirect('/clientes/lista/')
    if request.method != 'POST':
        form = ClienteForm(instance=cli, empresa=empresa, user=request.user)
        return render(request, 'clientes/att.html', {'form': form, 'cli': cli, 'error_messages': error_messages})
    form = ClienteForm(request.POST, instance=cli, empresa=empresa, user=request.user)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'clientes/att.html', {'form': form, 'cli': cli, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            c = form.save(commit=False)
            erro_limite = validar_limite_credito(c.limite_credito, c.vinc_fil, request.user)
            if erro_limite:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> {erro_limite}")
                return render(request, 'clientes/att.html', {'form': form, 'cli': cli, 'error_messages': error_messages})
            c.save()
            registrar_log(request, "ALTERAR", "Cliente", c.fantasia, f"Alterou o cadastro do cliente: {c.codigo} - {c.fantasia}", c.id, gerar_alteracoes(it_old, c))
            messages.success(request, 'Cliente atualizado com sucesso!')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('/clientes/lista/?tp=cod&s=' + str(c.codigo))
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
    return render(request, 'clientes/att.html', {'form': form, 'cli': cli, 'error_messages': error_messages})

@login_required
def del_cliente(request, codigo):
    if not request.user.has_perm('clientes.delete_cliente'):
        messages.info(request, 'Você não tem permissão para deletar clientes.')
        return redirect('/clientes/lista/')
    try:
        with transaction.atomic():
            cli = get_object_or_404(Cliente, codigo=codigo, vinc_emp=request.user.empresa)
            registrar_log(request, "EXCLUIR", "Cliente", cli.fantasia, f"Excluiu o cadastro do cliente: {cli.codigo} - {cli.fantasia}", cli.id, gerar_alteracoes(obj_antigo=cli))
            cli.delete()
            messages.success(request, 'Cliente deletado com sucesso!')
            return redirect('/clientes/lista/')
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
    return redirect('/clientes/lista/')