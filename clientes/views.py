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
    cli = request.GET.get('cl')

    # Lista de clientes filtrados
    clientes = Cliente.objects.filter(vinc_emp=request.user.empresa)

    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        clientes = clientes.filter(fantasia_normalizado__icontains=norm_s).order_by('fantasia')
    elif tp == 'cod' and s:
        try:
            clientes = clientes.filter(id__iexact=s).order_by('fantasia')
        except ValueError:
            clientes = Cliente.objects.none()

    clientes = clientes.annotate(
        dt_reg_sortable=Concat(Substr('dt_reg', 7, 4), Substr('dt_reg', 4, 2), Substr('dt_reg', 1, 2))
    )

    if p_dt == 'Sim' and dt_ini and dt_fim:
        try:
            dt_ini_dt = datetime.strptime(dt_ini, '%d/%m/%Y')
            dt_fim_dt = datetime.strptime(dt_fim, '%d/%m/%Y')
            dt_ini_sort = dt_ini_dt.strftime('%Y%m%d')
            dt_fim_sort = dt_fim_dt.strftime('%Y%m%d')
            clientes = clientes.filter(dt_reg_sortable__gte=dt_ini_sort, dt_reg_sortable__lte=dt_fim_sort)
        except ValueError:
            clientes = Cliente.objects.none()

    if f_s in ['Ativo', 'Inativo']:
        clientes = clientes.filter(situacao=f_s).order_by('fantasia')

    if t_pes in ['Física', 'Jurídica']:
        clientes = clientes.filter(pessoa=t_pes).order_by('fantasia')

    # Busca cliente selecionado
    cliente_selecionado = None
    if cli:
        cliente_selecionado = Cliente.objects.filter(id=cli, vinc_emp=request.user.filial_user).first()

    # Se o cliente selecionado não for compatível com os filtros, removemos ele
    if cliente_selecionado:
        if (f_s and cliente_selecionado.situacao != f_s) or (t_pes and cliente_selecionado.pessoa != t_pes):
            cliente_selecionado = None  # Cliente não será incluído na lista

    if reg == 'todos':
        num_pagina = clientes.count() or 1  # Mostra todas as filials
    else:
        try:
            num_pagina = int(reg)
        except ValueError:
            num_pagina = 10

    paginator = Paginator(clientes, num_pagina)
    page = request.GET.get('page')
    clientes = paginator.get_page(page)

    return render(request, 'clientes/lista.html', {
        'clientes': clientes,
        'cliente_selecionado': cliente_selecionado,  # Passa o cliente selecionado para a template
        'cli': cli,
        's': s,
        'tp': tp,
        't_pes': t_pes,
        'dt_ini': dt_ini,
        'dt_fim': dt_fim,
        'p_dt': p_dt,
        'reg': reg
    })


@login_required
def lista_clientes_ajax(request):
    term = request.GET.get('term', '').strip()

    clientes = Cliente.objects.filter(
        Q(id__icontains=term) | Q(fantasia__icontains=term)
    )[:10]

    clientes_data = []
    for cliente in clientes:
        clientes_data.append({
            'id': cliente.id,
            'fantasia': cliente.fantasia,
            'situacao': cliente.situacao,
            'cpfCnpj': cliente.cpf_cnpj,
            'email': cliente.email,
            'tel': cliente.tel,
            'endereco': cliente.endereco,
            'cep': cliente.cep,
            'numero': cliente.numero,
            'bairro': cliente.bairro.nome_bairro if cliente.bairro else '',
            'cidade': cliente.cidade.nome_cidade if cliente.cidade else '',
            'uf': cliente.uf.nome_estado if cliente.uf else ''
        })

    return JsonResponse({'clientes': clientes_data})

# @login_required
# def atualizar_empresas_em_massa(request):
#     if request.method == "POST":
#         empresas_ids = request.POST.getlist('multi')
#         email = request.POST.get('email_cont')
#         switch_emp = request.POST.get('switchEmp')
#         enviar_xml = request.POST.get('envio_xml1')  # Estado do envio XML obtido do select
#         switch_sit = request.POST.get('switchSit')
#         switch_principal = request.POST.get('switchId')
#         princ = request.POST.get('princip')
#         btn_sit = request.POST.get('btn_sit')
#         empresas = Empresa.objects.filter(id__in=empresas_ids)
#         if not empresas.exists():
#             messages.info(request, 'Nenhuma empresa selecionada.')
#             return redirect('/empresas/lista/')
#         alguma_alteracao = False
#         for empresa in empresas:
#             if switch_emp == 'on':  # Se houver alterações na empresa
#                 empresa.envio_xml = enviar_xml  # Atribui o valor selecionado do select
#                 alguma_alteracao = True
#             if switch_principal == 'on':  # Se houver alterações na empresa
#                 empresa.principal = princ  # Atribui o valor selecionado do select
#                 alguma_alteracao = True
#             elif switch_sit == 'on':  # Se houver alterações na empresa
#                 empresa.situacao = btn_sit
#                 alguma_alteracao = True
#             elif email:
#                 empresa.email_cont = email.lower()
#                 alguma_alteracao = True
#             empresa.save()
#         if alguma_alteracao and switch_emp == 'on' or switch_sit == 'on' or switch_principal == 'on': messages.success(request, 'Opção habilitada com sucesso!')
#         elif alguma_alteracao and email: messages.success(request, 'E-mail(s) inserido(s) com sucesso!')
#         else: messages.info(request, 'Nenhuma alteração realizada.')
#     else: messages.info(request, 'Nenhuma alteração realizada.')
#     return redirect('/empresas/lista/')

@login_required
def add_cliente(request):
    if not request.user.has_perm('clientes.add_cliente'):
        messages.info(request, 'Você não tem permissão para adicionar clientes.')
        return redirect('/clientes/lista/')
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False)

            bairro_id = request.POST.get('bairro')
            cidade_id = request.POST.get('cidade')
            estado_id = request.POST.get('uf')

            if bairro_id:
                try:
                    c.bairro = Bairro.objects.get(id=bairro_id)
                except Bairro.DoesNotExist:
                    c.bairro = None

            if cidade_id:
                try:
                    c.cidade = Cidade.objects.get(id=cidade_id)
                except Cidade.DoesNotExist:
                    c.cidade = None

            if estado_id:
                try:
                    c.uf = Estado.objects.get(id=estado_id)
                except Estado.DoesNotExist:
                    c.uf = None
            if request.user.is_authenticated:
                try:
                    c.vinc_emp = request.user.filial_user  # Busca a filial do usuário logado
                except Usuario.DoesNotExist:
                    return JsonResponse({'error': 'Usuário não possui filial vinculada'}, status=400)
            c.save()
            messages.success(request, 'Cliente adicionado com sucesso!')
            clie = str(c.id)
            return redirect('/clientes/lista/?tp=cod&s=' + clie)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'clientes/add_cliente.html', {'form': form, 'error_messages': error_messages})
    else: form = ClienteForm()
    return render(request, 'clientes/add_cliente.html', {'form': form})

@verifica_alguma_permissao(
    'clientes.add_cliente',
    'clientes.change_cliente',
    'clientes.delete_cliente'
)
@login_required
def att_cliente(request, id):
    cli = get_object_or_404(Cliente, pk=id)
    form = ClienteForm(instance=cli)
    if not request.user.has_perm('clientes.change_cliente'):
        messages.info(request, 'Você não tem permissão para editar clientes.')
        return redirect('/clientes/lista/')
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cli)
        if form.is_valid():
            cli.save()
            clie = str(cli.id)
            messages.success(request, 'Cliente atualizado com sucesso!')
            return redirect('/clientes/lista/?tp=cod&s=' + clie)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'clientes/att_cliente.html', {'form': form, 'cli': cli, 'error_messages': error_messages})
    else:
        return render(request, 'clientes/att_cliente.html', {'form': form, 'cli': cli})

@login_required
def del_cliente(request, id):
    if not request.user.has_perm('clientes.delete_cliente'):
        messages.info(request, 'Você não tem permissão para deletar clientes.')
        return redirect('/clientes/lista/')
    cli = get_object_or_404(Cliente, pk=id)
    cli.delete()
    messages.success(request, 'Cliente deletado com sucesso!')
    return redirect('/clientes/lista/')