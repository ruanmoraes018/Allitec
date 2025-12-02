from datetime import datetime, timedelta
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from util.permissoes import verifica_permissao, verifica_alguma_permissao
import json
from reportlab.pdfgen import canvas
from io import BytesIO
from django.http import HttpResponse
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
import os
from django.conf import settings
from util.permissoes import verifica_permissao
from PIL import Image
import ast
from django.db.models.functions import Concat, Substr
from decimal import Decimal
from django.views.decorators.http import require_POST
from reportlab.lib import colors
from django.contrib.auth.decorators import permission_required
from notifications.signals import notify
from filiais.models import Filial, Usuario
from .models import Entrada, EntradaProduto
from fornecedores.models import Fornecedor
from produtos.models import Produto
from .forms import EntradaForm, EntradaProdutoFormSet
from decimal import Decimal, InvalidOperation

def parse_decimal(value):
    if value is None or value == "":
        return Decimal("0")
    try:
        # substitui vírgula por ponto antes de converter
        return Decimal(str(value).replace(",", "."))
    except InvalidOperation:
        return Decimal("0")

@verifica_permissao('entradas.view_entrada')
@login_required
def lista_entradas(request):
    s = request.GET.get('s')
    f_s = request.GET.get('sit')
    tp_dt = request.GET.get('tp_dt')
    dt_ini = request.GET.get('dt_ini')
    dt_fim = request.GET.get('dt_fim')
    por_dt = request.GET.get('p_dt')
    cli = request.GET.get('cl')
    fil = request.GET.get('fil')
    reg = request.GET.get('reg', '10')
    hoje = datetime.today()

    entradas = Entrada.objects.filter(vinc_emp=request.user.empresa).prefetch_related("itens__produto")
    if s:
        entradas = entradas.filter(numeracao__icontains=s).order_by('numeracao')
    # Filtro por data
    if por_dt == 'Sim' and dt_ini and dt_fim:
        try:
            # Converter as datas de entrada de string para date
            dt_ini_dt = datetime.strptime(dt_ini, '%d/%m/%Y').date()
            dt_fim_dt = datetime.strptime(dt_fim, '%d/%m/%Y').date()

            if tp_dt == 'Emissão':
                entradas = entradas.filter(
                    dt_emi__range=(dt_ini_dt, dt_fim_dt)
                )
            elif tp_dt == 'Entrega':
                entradas = entradas.filter(
                    dt_ent__range=(dt_ini_dt, dt_fim_dt)
                )

        except ValueError:
            entradas = Entrada.objects.none()
    # Apenas aplica o filtro do dia atual se nenhum filtro estiver ativo
    filtros_ativos = any([
        s, f_s, por_dt == 'Sim', cli, tp_dt and tp_dt != 'Todos'
    ])
    if not filtros_ativos:
        entradas = entradas.filter(
            dt_emi=hoje,
            situacao='Pendente'
        )

    # Filtro por situação
    if f_s and f_s != 'Todos':
        entradas = entradas.filter(situacao=f_s)
    # Filtro por cliente
    fornecedor_selecionado = None
    if cli:
        fornecedor_selecionado = Fornecedor.objects.filter(id=cli, vinc_emp=request.user.empresa).first()
        if fornecedor_selecionado:
            entradas = entradas.filter(cli=fornecedor_selecionado)
    fornecedores = Fornecedor.objects.filter(vinc_emp=request.user.empresa)

   # Filtro por Filial
    filial_selecionada = None
    if fil:
        filial_selecionada = Filial.objects.filter(
            id=fil,
            vinc_emp=request.user.empresa
        ).first()
        if filial_selecionada:
            entradas = entradas.filter(vinc_emp=filial_selecionada)

    filiais = Filial.objects.filter(
        vinc_emp=request.user.empresa
    )

    # Paginação
    if reg == 'todos':
        num_pagina = entradas.count() or 1
    else:
        try:
            num_pagina = int(reg) if int(reg) > 0 else 10
        except ValueError:
            num_pagina = 10
    paginator = Paginator(entradas, num_pagina)
    page = request.GET.get('page')
    entradas = paginator.get_page(page)

    return render(request, 'entradas/lista.html', {
        'entradas': entradas,
        's': s,
        'fornecedor_selecionado': fornecedor_selecionado,
        'filial_selecionada': filial_selecionada,
        'cli': cli,
        'fornecedores': fornecedores,
        'filiais': filiais,
        'dt_ini': dt_ini,
        'dt_fim': dt_fim,
        'p_dt': por_dt,
        'tp_dt': tp_dt,
        'reg': reg,
    })

def entradas_por_produto(request, produto_id):
    entradas = EntradaProduto.objects.filter(produto_id=produto_id).select_related('entrada', 'entrada__fornecedor')

    data = []
    for ep in entradas:
        entrada = ep.entrada
        data.append({
            'entrada_id': entrada.id,
            'data': entrada.dt_ent.strftime('%d/%m/%Y') if entrada.dt_ent else '',
            'fornecedor': str(entrada.fornecedor),  # converte para string
            'quantidade': float(ep.quantidade),
            'valor_unitario': float(ep.preco_unitario),
            'total_entrada': float(entrada.total),  # 👈 total da entrada
        })

    return JsonResponse({'entradas': data})

@login_required
def add_entrada(request):
    # Verifica se o usuário tem permissão para adicionar entradas
    if not request.user.has_perm('entradas.add_entrada'):
        messages.info(request, 'Você não tem permissão para adicionar entradas de NF/Pedidos.')
        return redirect('/entradas/lista/')

    # Se a requisição for do tipo POST (formulário enviado)
    if request.method == "POST":
        # Cria uma instância do formulário com os dados enviados
        form = EntradaForm(request.POST)

        # Valida se o formulário está correto
        if form.is_valid():
            # Cria o objeto entrada sem salvar ainda no banco
            entrada = form.save(commit=False)
            entrada.save()  # Salva a entrada no banco

            # Dicionário para organizar os produtos enviados no POST
            produtos_dict = {}

            # Percorre todos os campos enviados no request.POST
            for key, value in request.POST.items():
                # Verifica se o campo pertence a produtos (produtos[...])
                if key.startswith("produtos["):
                    import re
                    # Extrai índice e campo usando regex → produtos[0][codigo], produtos[0][quantidade], etc.
                    m = re.match(r"produtos\[(\d+)\]\[(\w+)\]", key)
                    if m:
                        idx, campo = m.groups()  # Ex: idx = "0", campo = "codigo"
                        if idx not in produtos_dict:
                            produtos_dict[idx] = {}
                        produtos_dict[idx][campo] = value  # Armazena o valor do campo dentro do dicionário

            # Percorre os produtos organizados e os adiciona na entrada
            for dados in produtos_dict.values():
                try:
                    # Busca o produto no banco pelo código
                    produto = Produto.objects.get(pk=dados.get("codigo"))
                except Produto.DoesNotExist:
                    # Se não encontrar, mostra aviso e ignora este produto
                    messages.warning(request, f"Produto {dados.get('produto')} não encontrado e foi ignorado.")
                    continue

                # Cria ou atualiza o produto vinculado à entrada
                EntradaProduto.objects.update_or_create(
                    entrada=entrada,
                    produto=produto,
                    defaults={
                        "quantidade": parse_decimal(dados.get("quantidade")),
                        "preco_unitario": parse_decimal(dados.get("preco_unitario")),  # Usa 0 como padrão se não informado
                        "desconto": parse_decimal(dados.get("desconto")),
                    },
                )

            # Atualiza o valor total da entrada depois de salvar os produtos
            entrada.total = entrada.atualizar_total()
            entrada.save(update_fields=["total"])

            # Exibe mensagem de sucesso e redireciona para a lista de entradas
            messages.success(request, f'Registro de {entrada.tipo} - {entrada.numeracao} realizado com sucesso!')
            return redirect(f'/entradas/lista/?tp=numeracao&s={entrada.numeracao}')
        else:
            # Caso o formulário seja inválido, gera mensagens de erro personalizadas
            error_messages = []
            for field in form:
                for error in field.errors:
                    error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")

            # Renderiza novamente a página com os erros
            return render(request, "entradas/add.html", {
                "form": form,
                'error_messages': error_messages
            })
    else:
        # Se não for POST, apenas cria o formulário vazio
        form = EntradaForm()

    # Renderiza a página com o formulário
    return render(request, "entradas/add.html", {
        "form": form,
    })


@verifica_alguma_permissao(
    'entradas.add_entrada',
    'entradas.change_entrada',
    'entradas.delete_entrada'
)

@login_required
def att_entrada(request, id):
    # Busca a entrada no banco (ou retorna 404 se não existir)
    entrada = get_object_or_404(Entrada, pk=id)

    # Verifica se o usuário tem permissão de alteração
    if not request.user.has_perm('entradas.change_entrada'):
        messages.info(request, 'Você não tem permissão para editar entradas de NF/Pedidos.')
        return redirect('/entradas/lista/')

    if entrada.situacao == "Efetivada" and entrada.tipo == "Nota Fiscal":
        messages.warning(request, f'{entrada.tipo} - {entrada.numeracao} já efetivada, impossível alterar!')
        return redirect(f'/entradas/lista/?tp=numeracao&s={entrada.numeracao}')
    elif entrada.situacao == "Efetivada" and entrada.tipo == "Pedido":
        messages.warning(request, f'{entrada.tipo} - {entrada.numeracao} já efetivado, impossível alterar!')
        return redirect(f'/entradas/lista/?tp=numeracao&s={entrada.numeracao}')
    elif request.method == "POST":
        # Cria o formulário com os dados enviados e a instância existente
        form = EntradaForm(request.POST, instance=entrada)

        if form.is_valid():
            entrada = form.save(commit=False)
            entrada.save()

            # Dicionário temporário para os produtos
            produtos_dict = {}
            for key, value in request.POST.items():
                if key.startswith("produtos["):
                    import re
                    m = re.match(r"produtos\[(\d+)\]\[(\w+)\]", key)
                    if m:
                        idx, campo = m.groups()
                        if idx not in produtos_dict:
                            produtos_dict[idx] = {}
                        produtos_dict[idx][campo] = value

            # Atualiza os produtos da entrada
            produtos_ids = []
            for dados in produtos_dict.values():
                try:
                    produto = Produto.objects.get(pk=dados.get("codigo"))
                except Produto.DoesNotExist:
                    messages.warning(request, f"Produto {dados.get('produto')} não encontrado e foi ignorado.")
                    continue

                ep, created = EntradaProduto.objects.update_or_create(
                    entrada=entrada,
                    produto=produto,
                    defaults={
                        "quantidade": parse_decimal(dados.get("quantidade")),
                        "preco_unitario": parse_decimal(dados.get("preco_unitario")),
                        "desconto": parse_decimal(dados.get("desconto")),
                    },
                )
                produtos_ids.append(ep.id)

            # Atualiza o total da entrada
            entrada.total = entrada.atualizar_total()
            entrada.save(update_fields=["total"])

            messages.success(request, f'Registro de {entrada.tipo} - {entrada.numeracao} atualizado com sucesso!')
            return redirect(f'/entradas/lista/?tp=numeracao&s={entrada.numeracao}')
        else:
            error_messages = []
            for field in form:
                for error in field.errors:
                    error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, "entradas/att.html", {
                "form": form,
                "entrada": entrada,
                "error_messages": error_messages
            })
    else:
        # Se não for POST, carrega o formulário com os dados da entrada
        form = EntradaForm(instance=entrada)

    return render(request, "entradas/att.html", {
        "form": form,
        "entrada": entrada,
        "produtos": entrada.itens.all(),
    })


@login_required
def del_entrada(request, id):
    entrada = get_object_or_404(Entrada, pk=id)

    if not request.user.has_perm('entradas.delete_entrada'):
        messages.info(request, 'Você não tem permissão para deletar entradas de NF/Pedidos.')
        return redirect('/entradas/lista/')

    if entrada.situacao == "Efetivada" and entrada.tipo == "Nota Fiscal":
        messages.warning(request, f'{entrada.tipo} - {entrada.numeracao} já efetivada, impossível deletar!')
        return redirect(f'/entradas/lista/?tp=numeracao&s={entrada.numeracao}')
    else:
        messages.warning(request, f'{entrada.tipo} - {entrada.numeracao} já efetivado, impossível deletar!')
        return redirect(f'/entradas/lista/?tp=numeracao&s={entrada.numeracao}')

    if entrada.situacao != 'Pendente':
        messages.warning(request, 'NF/Pedidos só podem ser deletados com status <i>Pendente</i>!')
        return redirect(f'/entradas/lista/?tp=numero&s={entrada.numeracao}')

    entrada.delete()
    messages.success(request, f'Registro de {entrada.tipo} - {entrada.numeracao} deletado com sucesso!')
    return redirect('/entradas/lista/')

@require_POST
@login_required
def efetivar_entrada(request, id):
    entrada = get_object_or_404(Entrada, pk=id)

    if not request.user.has_perm('entradas.efetivar_entrada'):
        messages.info(request, 'Você não tem permissão para efetivar entradas de NF/Pedidos.')
        return redirect('/entradas/lista/')

    if request.method == 'POST':  # segurança extra
        if entrada.situacao == 'Pendente':
            entrada.situacao = "Efetivada"
            entrada.save()

            # Atualiza estoque e preço dos produtos da entrada
            for item in entrada.itens.all():
                produto = item.produto

                # Atualiza estoque
                produto.estoque_prod = (produto.estoque_prod or 0) + (item.quantidade or 0)

                # Atualiza preço de compra
                produto.vl_compra = str(item.preco_unitario)  # já que vl_compra é CharField

                produto.save(update_fields=["estoque_prod", "vl_compra"])

            messages.success(
                request,
                f'Registro de {entrada.tipo} - {entrada.numeracao} efetivado com sucesso!'
            )
        else:
            messages.warning(request, f'Entrada {entrada.numeracao} já foi efetivada antes.')

        return redirect(f'/entradas/lista/?tp=numeracao&s={entrada.numeracao}')

@require_POST
@login_required
def cancelar_entrada(request, id):
    entrada = get_object_or_404(Entrada, pk=id)

    if not request.user.has_perm('entradas.cancelar_entrada'):
        messages.info(request, 'Você não tem permissão para cancelar entradas de NF/Pedidos.')
        return redirect('/entradas/lista/')

    if request.method == 'POST':  # segurança extra
        if entrada.situacao == 'Efetivada':
            entrada.situacao = "Cancelada"
            entrada.save()

            # Atualiza estoque e preço dos produtos da entrada
            for item in entrada.itens.all():
                produto = item.produto

                # Atualiza estoque
                produto.estoque_prod = (produto.estoque_prod or 0) + (item.quantidade or 0)

                # Atualiza preço de compra
                produto.vl_compra = str(item.preco_unitario)  # já que vl_compra é CharField

                produto.save(update_fields=["estoque_prod", "vl_compra"])

            messages.success(
                request,
                f'Registro de {entrada.tipo} - {entrada.numeracao} cancelado com sucesso!'
            )
        else:
            messages.warning(request, f'Entrada {entrada.numeracao} já foi cancelada antes.')

        return redirect(f'/entradas/lista/?tp=numeracao&s={entrada.numeracao}')
