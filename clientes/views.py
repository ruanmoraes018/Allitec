from datetime import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Cliente
from .forms import ClienteForm
import unicodedata
from django.http import JsonResponse
from filiais.models import Usuario
from django.db.models.functions import Concat, Substr
from django.db.models import Q
from util.permissoes import verifica_permissao, verifica_alguma_permissao
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado

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
        clientes = clientes.filter(fantasia_normalizado__icontains=norm_s).order_by('fantasia')
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

@login_required
def add_cliente(request):
    if not request.user.has_perm('clientes.add_cliente'):
        messages.info(request, 'Você não tem permissão para adicionar clientes.')
        return redirect('/clientes/lista/')
    empresa = request.user.empresa
    if not empresa:
        messages.error(request, 'Erro crítico: Seu usuário não está vinculado a nenhuma empresa cadastrada.')
        return redirect('/clientes/lista/')
    if request.method == 'POST':
        form = ClienteForm(data=request.POST, empresa=empresa, user=request.user)
        if form.is_valid():
            c = form.save(commit=False)
            c.vinc_emp = empresa  # Busca a filial do usuário logado
            c.save()
            messages.success(request, 'Cliente adicionado com sucesso!')
            clie = str(c.codigo)
            return redirect('/clientes/lista/?tp=cod&s=' + clie)
        else:
            error_messages = []
            for field in form:
                if field.errors: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'clientes/add_cliente.html', {'form': form, 'error_messages': error_messages})
    else: form = ClienteForm(empresa=empresa, user=request.user)
    return render(request, 'clientes/add_cliente.html', {'form': form})

@verifica_alguma_permissao('clientes.add_cliente', 'clientes.change_cliente', 'clientes.delete_cliente')
@login_required
def att_cliente(request, codigo):
    cli = get_object_or_404(Cliente, codigo=codigo, vinc_emp=request.user.empresa)
    form = ClienteForm(instance=cli, empresa=request.user.empresa, user=request.user)
    if not request.user.has_perm('clientes.change_cliente'):
        messages.info(request, 'Você não tem permissão para editar clientes.')
        return redirect('/clientes/lista/')
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cli, empresa=request.user.empresa, user=request.user)
        if form.is_valid():
            form.save()
            next_url = request.POST.get('next') or request.GET.get('next')
            clie = str(cli.codigo)
            messages.success(request, 'Cliente atualizado com sucesso!')
            if next_url: return redirect(next_url)
            else: return redirect('/clientes/lista/?tp=cod&s=' + clie)
        else:
            error_messages = []
            for field in form:
                if field.errors: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'clientes/att_cliente.html', {'form': form, 'cli': cli, 'error_messages': error_messages})
    else: return render(request, 'clientes/att_cliente.html', {'form': form, 'cli': cli})

@login_required
def del_cliente(request, codigo):
    if not request.user.has_perm('clientes.delete_cliente'):
        messages.info(request, 'Você não tem permissão para deletar clientes.')
        return redirect('/clientes/lista/')
    cli = get_object_or_404(Cliente, codigo=codigo, vinc_emp=request.user.empresa)
    cli.delete()
    messages.success(request, 'Cliente deletado com sucesso!')
    return redirect('/clientes/lista/')