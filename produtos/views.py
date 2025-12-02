from datetime import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Produto, ProdutoTabela, CodigoProduto
from .forms import ProdutoForm
import unicodedata
from django.http import JsonResponse
from filiais.models import Usuario
from util.permissoes import verifica_permissao
from grupos.models import Grupo
from marcas.models import Marca
from unidades.models import Unidade
from tabelas_preco.models import TabelaPreco
from decimal import Decimal, InvalidOperation
import re

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('produtos.view_produto')
@login_required
def lista_produtos(request):
    s = request.GET.get('s', '').strip()
    tp = request.GET.get('tp')
    tp_produto = request.GET.get('tp_produto')
    grupo = request.GET.get('gp')
    marca = request.GET.get('marc')
    unid = request.GET.get('unid')
    reg = request.GET.get('reg', '10')
    sit = request.GET.get('sit')
    ordem = request.GET.get('ordem', 'desc_prod')

    # Produtos base
    produtos = Produto.objects.filter(vinc_emp=request.user.empresa)

    # Ordenação
    if ordem == '0':
        produtos = produtos.order_by('desc_prod')
    elif ordem == '1':
        produtos = produtos.order_by('id')
    else:
        produtos = produtos.order_by(ordem)

    # FILTRO DE BUSCA
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        produtos = produtos.filter(desc_normalizado__icontains=norm_s)

    elif tp == 'cod':
        if s:
            try:
                produtos = produtos.filter(id__iexact=s)
            except ValueError:
                produtos = Produto.objects.none()
        else:
            # Se s está vazio, não aplica filtro -> lista todos
            pass

    # Tipo de produto
    if tp_produto in ['Principal', 'Adicional']:
        produtos = produtos.filter(tp_prod__exact=tp_produto)

    # Situação
    if sit == '1':
        produtos = produtos.filter(situacao='Ativo')
    elif sit == '2':
        produtos = produtos.filter(situacao='Inativo')

    # Grupo
    grupo_selecionado = None
    if grupo:
        grupo_selecionado = Grupo.objects.filter(id=grupo, vinc_emp=request.user.empresa).first()
        if grupo_selecionado:
            produtos = produtos.filter(grupo=grupo_selecionado)
    grupos = Grupo.objects.filter(vinc_emp=request.user.empresa)

    # Marca
    marca_selec = None
    if marca:
        marca_selec = Marca.objects.filter(id=marca, vinc_emp=request.user.empresa).first()
        if marca_selec:
            produtos = produtos.filter(marca=marca_selec)
    marcas = Marca.objects.filter(vinc_emp=request.user.empresa)

    # Unidade
    unidade_selecionado = None
    if unid:
        unidade_selecionado = Unidade.objects.filter(id=unid, vinc_emp=request.user.empresa).first()
        if unidade_selecionado:
            produtos = produtos.filter(unidProd=unidade_selecionado)
    unidades = Unidade.objects.filter(vinc_emp=request.user.empresa)

    # Tabelas de preço
    for p in produtos:
        tabelas = ProdutoTabela.objects.filter(produto=p)
        p.tab_conv = [
            {
                "id": tab.id,
                "descricao": tab.tabela.descricao if hasattr(tab, 'tabela') else str(tab),
                "vl_prod": float(tab.vl_prod)
            }
            for tab in tabelas
        ]

    # Paginação
    if reg == 'todos':
        num_pagina = produtos.count() or 1
    else:
        try:
            num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError:
            num_pagina = 10  # padrão

    paginator = Paginator(produtos, num_pagina)
    page = request.GET.get('page')
    produtos = paginator.get_page(page)

    return render(request, 'produtos/lista.html', {
        'produtos': produtos,
        's': s,
        'tp': tp,
        'sit': sit,
        'ordem': ordem,
        'marca_selec': marca_selec,
        'marca': marca,
        'marcas': marcas,
        'grupo_selecionado': grupo_selecionado,
        'grupo': grupo,
        'grupos': grupos,
        'unidade_selecionado': unidade_selecionado,
        'unidades': unidades,
        'unid': unid,
        'reg': reg,
        'tp_produto': tp_produto
    })


@login_required
def att_prod_lote(request):
    if request.method == "POST":
        produtos_ids = request.POST.getlist('multi')
        switch_grupo = request.POST.get('switchSit')
        switch_unidade = request.POST.get('switchEmp')
        switch_marca = request.POST.get('switchMarca')
        switch_lista_orc = request.POST.get('switchListaOrc')

        unidade_id = request.POST.get('unid1')
        grupo_id = request.POST.get('gp1')
        marca_id = request.POST.get('marca1')

        produtos = Produto.objects.filter(id__in=produtos_ids, vinc_emp=request.user.empresa)
        if not produtos.exists():
            messages.info(request, 'Nenhum produto selecionado.')
            return redirect('/produtos/lista/')

        alguma_alteracao = False

        for produto in produtos:
            if switch_grupo == 'on' and grupo_id:
                gp = Grupo.objects.get(id=grupo_id)
                produto.grupo = gp
                alguma_alteracao = True
            if switch_unidade == 'on' and unidade_id:
                unidade = Unidade.objects.get(id=unidade_id)
                produto.unidProd = unidade
                alguma_alteracao = True
            if switch_lista_orc == 'on':
                produto.lista_orc = True
                alguma_alteracao = True
            if switch_marca == 'on' and marca_id:
                marca = Marca.objects.get(id=marca_id)
                produto.marca = marca
                alguma_alteracao = True
            produto.save()

        if alguma_alteracao:
            messages.success(request, 'Campos atualizados com sucesso!')
        else:
            messages.info(request, 'Nenhuma alteração realizada.')
    else:
        messages.info(request, 'Nenhuma alteração realizada.')
    return redirect('/produtos/lista/')

@login_required
def att_preco_lote(request):
    if request.method == "POST":
        produtos_ids = request.POST.getlist('prod-prec')
        tabela_id = request.POST.get('tb-prec')
        tp_atrib = request.POST.get('tp-atrib')  # 0 = Margem, 1 = Valor
        campo_1 = request.POST.get('campo_1', '').replace(',', '.').strip()
        campo_2 = request.POST.get('campo_2', '').replace(',', '.').strip()

        produtos = Produto.objects.filter(id__in=produtos_ids, vinc_emp=request.user.empresa)

        if not produtos.exists():
            messages.info(request, 'Nenhum produto selecionado.')
            return redirect('/produtos/lista/')

        try:
            tabela = TabelaPreco.objects.get(id=tabela_id)
        except TabelaPreco.DoesNotExist:
            messages.error(request, 'Tabela de preço não encontrada.')
            return redirect('/produtos/lista/')

        try:
            val_1 = Decimal(campo_1 or '0')
            val_2 = Decimal(campo_2 or '0')
        except InvalidOperation:
            messages.error(request, "Os valores informados são inválidos.")
            return redirect('/produtos/lista/')

        alguma_alteracao = False

        for p in produtos:
            try:
                vl_compra = Decimal(p.vl_compra or '0')
            except InvalidOperation:
                vl_compra = Decimal('0')

            if tp_atrib == "0":  # ATRIBUIR POR MARGEM
                margem = val_1
                vl_prod = vl_compra * (Decimal('1') + margem / Decimal('100'))
            elif tp_atrib == "1":  # ATRIBUIR POR VALOR
                vl_prod = val_1
                margem = ((vl_prod - vl_compra) / vl_compra * Decimal('100')) if vl_compra > 0 else Decimal('0')
            else:
                messages.warning(request, f"Tipo de atribuição inválido ({tp_atrib}).")
                continue

            ProdutoTabela.objects.update_or_create(
                produto=p,
                tabela=tabela,
                defaults={
                    'vl_prod': vl_prod,
                    'margem': margem
                }
            )
            alguma_alteracao = True

        if alguma_alteracao:
            tipo_label = "margem" if tp_atrib == "0" else "valor"
            messages.success(request, f"Tabela de preço atualizada com base em {tipo_label} com sucesso!")
        else:
            messages.info(request, 'Nenhuma alteração realizada.')

    return redirect('/produtos/lista/')


@login_required
def buscar_produtos(request):
    termo = request.GET.get('s', '').strip()
    filtro = request.GET.get('tp', 'desc')  # 'desc' ou 'cod'
    tp_produto = request.GET.get('tp_prod', '')  # 'Principal', 'Adicional' ou vazio

    if filtro == 'desc':
        norm_termo = remove_accents(termo).lower()
        produtos = Produto.objects.filter(
            desc_normalizado__icontains=norm_termo,
            lista_orc=True
        )

        if tp_produto:
            produtos = produtos.filter(tp_prod__icontains=tp_produto)

        produtos = produtos.order_by('id')

    else:  # filtro == 'cod'
        if termo:
            produtos = Produto.objects.filter(id=termo)
            if tp_produto:
                produtos = produtos.filter(tp_prod__icontains=tp_produto)
        else:
            produtos = Produto.objects.none()

    # 🔹 Monta o JSON incluindo valores da tabela de preços
    data = []
    for prod in produtos:
        # Pega o preço da tabela relacionada (por exemplo, a primeira)
        tabela = prod.produtotabela_set.first()  # ou use .filter(ativo=True).first() se houver campo de status

        data.append({
            'id': prod.id,
            'desc_prod': prod.desc_prod,
            'unidProd': prod.unidProd.nome_unidade if prod.unidProd else '',
            'grupo': prod.grupo.nome_grupo if prod.grupo else '',
            'estoque_prod': getattr(prod, 'estoque_prod', None),
            'vl_compra': prod.vl_compra,
            'vl_prod': tabela.vl_prod if tabela else None,
            'tp_prod': prod.tp_prod,
        })

    return JsonResponse({'produtos': data})


@login_required
def buscar_produtos_ent(request):
    termo = request.GET.get('s', '').strip()
    filtro = request.GET.get('tp', 'desc')
    tp_produto = request.GET.get('tp_prod', '')
    gp_produto = request.GET.get('gp_prod', '')
    unid_produto = request.GET.get('unid_prod', '')
    num_pagina = request.GET.get('num_pag', '10')
    page = request.GET.get('page', 1)

    if filtro == 'desc':
        norm_termo = remove_accents(termo).lower()
        produtos = Produto.objects.filter(desc_normalizado__icontains=norm_termo).prefetch_related('produtotabela_set')

        if tp_produto:
            produtos = produtos.filter(tp_prod__icontains=tp_produto)
        if gp_produto:
            produtos = produtos.filter(grupo=gp_produto)
        if unid_produto:
            produtos = produtos.filter(unidProd=unid_produto)

        produtos = produtos.order_by('id')

    else:
        if termo:
            produtos = Produto.objects.filter(id=termo)
            if tp_produto:
                produtos = produtos.filter(tp_prod__icontains=tp_produto)
        else:
            produtos = Produto.objects.none()

    # 🔹 Paginação
    if num_pagina == 'todos':
        qtd_pag = produtos.count() or 1
    else:
        try:
            qtd_pag = int(num_pagina) if int(num_pagina) > 0 else 1
        except ValueError:
            qtd_pag = 10

    paginator = Paginator(produtos, qtd_pag)
    produtos_page = paginator.get_page(page)

    # 🔹 Monta manualmente o JSON incluindo valores da tabela de preços
    data = []
    for prod in produtos_page.object_list:
        tabela = prod.produtotabela_set.first()  # ou .filter(padrao=True).first() se houver campo 'padrao'

        data.append({
            'id': prod.id,
            'desc_prod': prod.desc_prod,
            'unidProd': prod.unidProd.nome_unidade if prod.unidProd else '',
            'grupo': prod.grupo.nome_grupo if prod.grupo else '',
            'estoque_prod': getattr(prod, 'estoque_prod', None),
            'vl_compra': prod.vl_compra,
            'vl_prod': tabela.vl_prod if tabela else None,
            'tp_prod': prod.tp_prod,
        })

    return JsonResponse({
        'produtos': data,
        'page': produtos_page.number,
        'num_pages': paginator.num_pages,
        'has_next': produtos_page.has_next(),
        'has_prev': produtos_page.has_previous(),
    })


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

def str_para_decimal(valor_str):
    """
    Converte uma string para Decimal, removendo caracteres não numéricos,
    aceitando vírgula como separador decimal.
    """
    if not valor_str:
        return Decimal('0.00')

    # Remove tudo que não seja número, vírgula ou ponto
    valor_limpo = re.sub(r'[^\d,.-]', '', valor_str)

    # Troca vírgula por ponto (para Decimal)
    valor_limpo = valor_limpo.replace(',', '.')

    try:
        return Decimal(valor_limpo)
    except InvalidOperation:
        return Decimal('0.00')

@login_required
def add_produto(request):
    if request.method == 'POST':
        form = ProdutoForm(request.POST)
        lista_orc = request.POST.get('lista_orc') == 'on'

        if form.is_valid():
            p = form.save(commit=False)

            if request.user.is_authenticated:
                try:
                    p.vinc_emp = request.user.empresa
                except Usuario.DoesNotExist:
                    return JsonResponse({'error': 'Usuário não possui filial vinculada'}, status=400)

            p.lista_orc = lista_orc
            p.save()

            # ===============================
            # 🔹 Lê as tabelas de preço enviadas
            # ===============================
            tab_preco_dict = {}
            for key, value in request.POST.items():
                if key.startswith("tab_preco["):
                    import re
                    m = re.match(r"tab_preco\[(\d+)\]\[(\w+)\]", key)
                    if m:
                        idx, campo = m.groups()
                        if idx not in tab_preco_dict:
                            tab_preco_dict[idx] = {}
                        tab_preco_dict[idx][campo] = value

            # 🔹 Cria registros de ProdutoTabela
            for dados in tab_preco_dict.values():
                tabela_id = dados.get("tabela")
                margem = dados.get("margem")
                vl_prod = dados.get("vl_prod")

                if not tabela_id or not vl_prod:
                    continue

                try:
                    tabela = TabelaPreco.objects.get(pk=tabela_id)
                except TabelaPreco.DoesNotExist:
                    messages.warning(request, f"Tabela {tabela_id} não encontrada.")
                    continue
                try:
                    vl_prod_decimal = Decimal(str(vl_prod).replace(',', '.'))
                except InvalidOperation:
                    vl_prod_decimal = Decimal('0.00')  # valor padrão caso a conversão falhe

                ProdutoTabela.objects.create(
                    produto=p,
                    tabela=tabela,
                    vl_prod=vl_prod_decimal,
                    margem=Decimal(margem or 0)
                )
            # Código Secundário
            cod_sec_dict = {}
            for key, value in request.POST.items():
                if key.startswith("codigo["):
                    import re
                    m = re.match(r"codigo\[(\d+)\]\[(\w+)\]", key)
                    if m:
                        idx, campo = m.groups()
                        if idx not in cod_sec_dict:
                            cod_sec_dict[idx] = {}
                        cod_sec_dict[idx][campo] = value

            for dados in cod_sec_dict.values():
                codigo = dados.get("codigo", "").strip()

                if not codigo:
                    continue

                # Verifica se já existe esse código para outro produto
                if CodigoProduto.objects.filter(codigo=codigo).exists():
                    messages.warning(request, f"O código '{codigo}' já está vinculado a outro produto.")
                    continue

                # Cria o código vinculado ao produto atual
                CodigoProduto.objects.create(produto=p, codigo=codigo)

            messages.success(request, 'Produto adicionado com sucesso!')
            return redirect(f'/produtos/lista/?tp=cod&s={p.id}')

        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(
                            f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!"
                        )

            return render(
                request,
                'produtos/add_produto.html',
                {'form': form, 'error_messages': error_messages}
            )

    else:
        form = ProdutoForm()

    return render(request, 'produtos/add_produto.html', {'form': form})

@login_required
def att_produto(request, id):
    p = get_object_or_404(Produto, pk=id)
    form = ProdutoForm(instance=p)

    if not request.user.has_perm('produtos.change_produto'):
        messages.info(request, 'Você não tem permissão para editar produtos.')
        return redirect('/produtos/lista/')

    if request.method == 'POST':
        form = ProdutoForm(request.POST, instance=p)
        lista_orc = request.POST.get('lista_orc') == 'on'

        if form.is_valid():
            estoque_atual = p.estoque_prod
            p = form.save(commit=False)

            # se o campo estoque não foi preenchido, mantém o valor anterior
            if not p.estoque_prod:
                p.estoque_prod = estoque_atual

            p.lista_orc = lista_orc
            p.save()

            # ======================
            # 🔹 Atualiza tabelas de preço
            # ======================
            tab_preco_dict = {}
            for key, value in request.POST.items():
                if key.startswith("tab_preco["):
                    import re
                    m = re.match(r"tab_preco\[(\d+)\]\[(\w+)\]", key)
                    if m:
                        idx, campo = m.groups()
                        if idx not in tab_preco_dict:
                            tab_preco_dict[idx] = {}
                        tab_preco_dict[idx][campo] = value

            tab_preco_ids = []
            for dados in tab_preco_dict.values():
                tabela_id = dados.get("tabela")
                margem = dados.get("margem")
                vl_prod = dados.get("vl_prod")

                if not tabela_id or not vl_prod:
                    continue

                try:
                    tabela = TabelaPreco.objects.get(pk=tabela_id)
                except TabelaPreco.DoesNotExist:
                    messages.warning(request, f"Tabela {tabela_id} não encontrada.")
                    continue

                vl_prod_decimal = str_para_decimal(vl_prod)
                margem_decimal = str_para_decimal(margem)

                ep, created = ProdutoTabela.objects.update_or_create(
                    produto=p,
                    tabela=tabela,
                    defaults={
                        'vl_prod': vl_prod_decimal,
                        'margem': margem_decimal
                    }
                )
                tab_preco_ids.append(ep.id)

            # Código Secundário
            cod_sec_dict = {}
            for key, value in request.POST.items():
                if key.startswith("codigo["):
                    import re
                    m = re.match(r"codigo\[(\d+)\]\[(\w+)\]", key)
                    if m:
                        idx, campo = m.groups()
                        if idx not in cod_sec_dict:
                            cod_sec_dict[idx] = {}
                        cod_sec_dict[idx][campo] = value

            cod_sec_ids = []

            for dados in cod_sec_dict.values():
                codigo = dados.get("codigo", "").strip()
                if not codigo:
                    continue

                # ⚠️ Verifica se o código já está vinculado a outro produto
                if CodigoProduto.objects.filter(codigo=codigo).exclude(produto=p).exists():
                    messages.warning(request, f"O código '{codigo}' já está vinculado a outro produto.")
                    continue

                # 🔹 Cria ou obtém o código vinculado ao produto atual
                ep, created = CodigoProduto.objects.get_or_create(produto=p, codigo=codigo)
                cod_sec_ids.append(ep.id)

            # 🔥 Remove códigos antigos que não foram reenviados
            CodigoProduto.objects.filter(produto=p).exclude(id__in=cod_sec_ids).delete()

            ProdutoTabela.objects.filter(produto=p).exclude(id__in=tab_preco_ids).delete()

            messages.success(request, 'Produto atualizado com sucesso!')
            return redirect(f'/produtos/lista/?tp=cod&s={p.id}')

        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'produtos/att_produto.html', {'form': form, 'p': p, 'error_messages': error_messages})

    todas_tabelas = TabelaPreco.objects.all()  # para o select de adicionar nova tabela
    prod_tabelas = p.produtotabela_set.all()   # para preencher as linhas existentes


    return render(request, 'produtos/att_produto.html', {
        'form': form,
        'p': p,
        'tabelas': todas_tabelas,
        'prod_tabelas': prod_tabelas,
        "codigos": p.codigos.all(),
    })


@login_required
def clonar_produto(request, id):
    p = get_object_or_404(Produto, pk=id)

    if not request.user.has_perm('produtos.clonar_produto'):
        messages.info(request, 'Você não tem permissão para clonar produtos.')
        return redirect('/produtos/lista/')

    if request.method == 'POST':
        form = ProdutoForm(request.POST)
        lista_orc = request.POST.get('lista_orc') == 'on'

        if form.is_valid():
            # 🔹 Cria o novo produto
            novo_produto = form.save(commit=False)
            if request.user.is_authenticated:
                try:
                    novo_produto.vinc_emp = request.user.empresa
                except Usuario.DoesNotExist:
                    return JsonResponse({'error': 'Usuário não possui filial vinculada'}, status=400)

            novo_produto.lista_orc = lista_orc
            novo_produto.save()

            # ======================
            # 🔹 Clonar tabelas de preço do produto original
            # ======================
            tab_preco_dict = {}
            for key, value in request.POST.items():
                if key.startswith("tab_preco["):
                    import re
                    m = re.match(r"tab_preco\[(\d+)\]\[(\w+)\]", key)
                    if m:
                        idx, campo = m.groups()
                        if idx not in tab_preco_dict:
                            tab_preco_dict[idx] = {}
                        tab_preco_dict[idx][campo] = value

            tab_preco_ids = []
            for dados in tab_preco_dict.values():
                tabela_id = dados.get("tabela")
                margem = dados.get("margem")
                vl_prod = dados.get("vl_prod")

                if not tabela_id or not vl_prod:
                    continue

                try:
                    tabela = TabelaPreco.objects.get(pk=tabela_id)
                except TabelaPreco.DoesNotExist:
                    messages.warning(request, f"Tabela {tabela_id} não encontrada.")
                    continue

                vl_prod_decimal = str_para_decimal(vl_prod)
                margem_decimal = str_para_decimal(margem)

                ep = ProdutoTabela.objects.create(
                    produto=novo_produto,
                    tabela=tabela,
                    vl_prod=vl_prod_decimal,
                    margem=margem_decimal
                )
                tab_preco_ids.append(ep.id)

            # Se nenhuma tabela foi enviada via POST, clona as existentes do produto original
            if not tab_preco_ids:
                for tabela_antiga in p.produtotabela_set.all():
                    ProdutoTabela.objects.create(
                        produto=novo_produto,
                        tabela=tabela_antiga.tabela,
                        vl_prod=tabela_antiga.vl_prod,
                        margem=tabela_antiga.margem
                    )
            # Código Secundário
            cod_sec_dict = {}
            for key, value in request.POST.items():
                if key.startswith("codigo["):
                    import re
                    m = re.match(r"codigo\[(\d+)\]\[(\w+)\]", key)
                    if m:
                        idx, campo = m.groups()
                        if idx not in cod_sec_dict:
                            cod_sec_dict[idx] = {}
                        cod_sec_dict[idx][campo] = value

            for dados in cod_sec_dict.values():
                codigo = dados.get("codigo", "").strip()

                if not codigo:
                    continue

                # Verifica se já existe esse código para outro produto
                if CodigoProduto.objects.filter(codigo=codigo).exists():
                    messages.warning(request, f"O código '{codigo}' já está vinculado a outro produto.")
                    continue

                # Cria o código vinculado ao produto atual
                CodigoProduto.objects.create(produto=p, codigo=codigo)

            messages.success(request, 'Produto clonado com sucesso!')
            return redirect(f'/produtos/lista/?tp=cod&s={novo_produto.id}&tp_produto={novo_produto.tp_prod}')

        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(
                            f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!"
                        )
            return render(request, 'produtos/clonar.html', {'form': form, 'error_messages': error_messages})

    else:
        # Preenche o formulário com os dados do produto existente
        form = ProdutoForm(instance=p)
        form.fields['estoque_prod'].initial = 0.00  # Zerado no clone

    # 🔹 Envia também as tabelas de preço atuais do produto original
    todas_tabelas = TabelaPreco.objects.all()
    prod_tabelas = p.produtotabela_set.all()

    return render(request, 'produtos/clonar.html', {
        'form': form,
        'p': p,
        'tabelas': todas_tabelas,
        'prod_tabelas': prod_tabelas
    })


@login_required
def del_produto(request, id):
    if not request.user.has_perm('produtos.delete_produto'):
        messages.info(request, 'Você não tem permissão para deletar produtos.')
        return redirect('/produtos/lista/')
    p = get_object_or_404(Produto, pk=id)
    p.delete()
    messages.success(request, 'Produto deletado com sucesso!')
    return redirect('/produtos/lista/')