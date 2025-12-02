from django.shortcuts import render, redirect, get_object_or_404
from .models import Empresa
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from datetime import datetime
import unicodedata
from django.core.paginator import Paginator
from .forms import EmpresaForm
from util.permissoes import verifica_permissao
from filiais.models import Filial, Usuario
from clientes.models import Cliente
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado
from django.http import JsonResponse

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('empresas.view_empresa')
@login_required
def lista_empresas(request):
    s = request.GET.get('s')               # texto de busca
    tp = request.GET.get('tp')             # tipo de busca (desc ou cod)
    f_s = request.GET.get('sit')           # situação: Ativa / Inativa
    t_pes = request.GET.get('t_pes')       # tipo pessoa: Física / Jurídica
    dt_ini = request.GET.get('dt_ini')     # data inicial
    dt_fim = request.GET.get('dt_fim')     # data final
    p_dt = request.GET.get('p_dt')         # filtrar por data? Sim / Não
    reg = request.GET.get('reg', '10')     # registros por página
    dia_venc = request.GET.get('dia_venc')

    # Filtrar filiais que pertencem à filial principal logada
    empresas = Empresa.objects.all().order_by('fantasia')

    # Filtro por nome (fantasia)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        empresas = empresas.filter(fantasia_normalizado__icontains=norm_s).order_by('fantasia')

    # Filtro por código (ID)
    elif tp == 'cod' and s:
        try:
            empresas = empresas.filter(id__icontains=s).order_by('fantasia')
        except ValueError:
            empresas = Empresa.objects.none()
    if dia_venc in ['05', '10', '15', '20', '25', '30']:
        empresas = empresas.filter(dia_venc=dia_venc)
    # Filtro por data de nascimento (ou qualquer outro campo de data adaptado)
    if p_dt == 'Sim' and dt_ini and dt_fim:
        try:
            dt_ini_dt = datetime.strptime(dt_ini, '%d/%m/%Y').date()
            dt_fim_dt = datetime.strptime(dt_fim, '%d/%m/%Y').date()
            empresas = empresas.filter(dt_criacao__range=(dt_ini_dt, dt_fim_dt))
        except ValueError:
            empresas = Empresa.objects.none()

    # Filtro por situação (ativa/inativa)
    if f_s in ['Ativa', 'Inativa']:
        empresas = empresas.filter(situacao=f_s)

    # Filtro por tipo de pessoa (física/jurídica) - caso use esse campo na model
    if t_pes in ['Física', 'Jurídica']:
        empresas = empresas.filter(pessoa=t_pes)

    # Paginação
    if reg == 'todos':
        num_pagina = empresas.count() or 1
    else:
        try:
            num_pagina = int(reg)
        except ValueError:
            num_pagina = 10

    paginator = Paginator(empresas, num_pagina)
    page = request.GET.get('page')
    empresas = paginator.get_page(page)

    return render(request, 'empresas/lista.html', {
        'empresas': empresas,
        's': s,
        'tp': tp,
        't_pes': t_pes,
        'dt_ini': dt_ini,
        'dt_fim': dt_fim,
        'p_dt': p_dt,
        'dia_venc': dia_venc,
        'reg': reg
    })

@login_required
def lista_empresas_ajax(request):
    termo_busca = request.GET.get('term', '')

    try:
        empresas = Empresa.objects.filter(
            situacao='Ativa',
            fantasia__icontains=termo_busca
        ).values('id', 'fantasia')

        results = [{'id': emp['id'], 'text': emp['fantasia'].upper()} for emp in empresas]

        return JsonResponse({'results': results})

    except Usuario.DoesNotExist:
        return JsonResponse({'results': []})

@login_required
def add_empresa(request):
    if not request.user.has_perm('empresas.add_empresa'):
        messages.info(request, 'Você não tem permissão para adicionar empresas.')
        return redirect('/empresas/lista/')

    if request.method == 'POST':
        form = EmpresaForm(request.POST, request.FILES)
        if form.is_valid():
            nova_empresa = form.save(commit=False)
            nova_empresa.situacao = 'Ativa'
            logo = request.FILES.get('logo')

            # Define logo padrão caso não tenha enviado
            if logo:
                nova_empresa.logo = logo
            else:
                nova_empresa.logo = 'media/default_logo.png'

            nova_empresa.save()


            # Se gerar filial estiver marcado
            if nova_empresa.gerar_filial is True:
                nova_filial, created = Filial.objects.get_or_create(
                    situacao='Ativa',
                    cnpj=nova_empresa.cnpj,
                    ie=nova_empresa.ie,
                    razao_social=nova_empresa.razao_social,
                    fantasia=nova_empresa.fantasia,
                    endereco=nova_empresa.endereco,
                    cep=nova_empresa.cep,
                    numero=nova_empresa.numero,
                    bairro_fil=nova_empresa.bairro_emp,
                    complem=nova_empresa.complem,
                    cidade_fil=nova_empresa.cidade_emp,
                    uf=nova_empresa.uf_emp,
                    tel=nova_empresa.tel,
                    email=nova_empresa.email,
                    fantasia_normalizado=nova_empresa.fantasia_normalizado,
                    principal=True,
                    logo=nova_empresa.logo,
                )


                # 🔥 Criar Cliente padrão 'CONSUMIDOR'
                novo_cliente, created = Cliente.objects.get_or_create(
                    situacao='Ativo',
                    pessoa="Física",
                    cpf_cnpj='.',
                    ie='.',
                    razao_social='CONSUMIDOR',
                    fantasia='CONSUMIDOR',
                    endereco='.',
                    cep='.',
                    numero='.',
                    bairro=nova_empresa.bairro_emp,
                    complem='.',
                    cidade=nova_empresa.cidade_emp,
                    uf=nova_empresa.uf_emp,
                    tel='.',
                    email='.',
                )

                if created:
                    nova_filial.save()
                    novo_cliente.save()
                    novo_bairro, criado = Bairro.objects.get_or_create(
                        nome_bairro=nova_filial.bairro_fil,
                        vinc_emp=nova_filial
                    )
                    novo_cidade, criado = Cidade.objects.get_or_create(
                        nome_cidade=nova_filial.cidade_fil,
                        vinc_emp=nova_filial
                    )
                    novo_estado, criado = Estado.objects.get_or_create(
                        nome_estado=nova_filial.uf,
                        vinc_emp=nova_filial
                    )
                    print("Nova filial cadastrada")
                    print("Novo cliente cadastrado")
                    if criado:
                        print("Novo bairro cadastrado")
                        print("Nova cidade cadastrada")
                        print("Novo estado cadastrado")

            messages.success(request, 'Empresa cadastrada com sucesso.')
            return redirect('/empresas/lista/')

        else:
            # Monta mensagens de erro personalizadas
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(
                            f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!"
                        )
            return render(request, 'empresas/add.html', {'form': form, 'error_messages': error_messages})

    else:
        form = EmpresaForm()

    return render(request, 'empresas/add.html', {'form': form})


@login_required
def att_empresa(request, id):
    empresa = get_object_or_404(Empresa, id=id)
    form = EmpresaForm(instance=empresa)
    if not request.user.has_perm('empresas.change_empresa'):
        messages.info(request, 'Você não tem permissão para editar empresas.')
        return redirect('/empresas/lista/')
    if request.method == 'POST':
        form = EmpresaForm(request.POST, request.FILES, instance=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Empresa atualizada com sucesso.')
            return redirect('/empresas/lista/')
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'empresas/att.html', {'form': form, 'empresa': empresa, 'error_messages': error_messages})
    else:
        form = EmpresaForm(instance=empresa)

    return render(request, 'empresas/att.html', {'form': form, 'empresa': empresa})

@login_required
def del_empresa(request, id):
    empresa = get_object_or_404(Empresa, id=id)

    if not request.user.has_perm('empresas.delete_empresa'):
        messages.info(request, 'Você não tem permissão para deletar empresas.')
        return redirect('/empresas/lista/')

    if request.method == 'POST':
        empresa.delete()
        messages.success(request, 'Empresa excluída com sucesso.')
        return redirect('/empresas/lista/')
    return render(request, 'empresas/del_empresa.html')
