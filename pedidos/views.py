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
from PIL import Image
import ast
from django.db.models.functions import Concat, Substr
from decimal import Decimal
from django.views.decorators.http import require_POST
from reportlab.lib import colors
from django.contrib.auth.decorators import permission_required
from notifications.signals import notify
from filiais.models import Filial, Usuario
from .models import Pedido, PedidoProduto
from clientes.models import Cliente
from produtos.models import Produto
from .forms import PedidoForm, PedidoProdutoFormSet
from decimal import Decimal, InvalidOperation

def parse_decimal(value):
    if value is None or value == "":
        return Decimal("0")
    try:
        # substitui vírgula por ponto antes de converter
        return Decimal(str(value).replace(",", "."))
    except InvalidOperation:
        return Decimal("0")

@verifica_permissao('pedidos.view_pedido')
@login_required
def lista_pedidos(request):
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

    pedidos = Pedido.objects.filter(vinc_emp=request.user.empresa).prefetch_related("itens__produto")
    if s:
        pedidos = pedidos.filter(id__iexact=s).order_by('id')
    # Filtro por data
    if por_dt == 'Sim' and dt_ini and dt_fim:
        try:
            # Converter as datas de pedido de string para date
            dt_ini_dt = datetime.strptime(dt_ini, '%d/%m/%Y').date()
            dt_fim_dt = datetime.strptime(dt_fim, '%d/%m/%Y').date()

            if tp_dt == 'Emissão':
                pedidos = pedidos.filter(
                    dt_emi__range=(dt_ini_dt, dt_fim_dt)
                )
            elif tp_dt == 'Fatura':
                pedidos = pedidos.filter(
                    dt_fat__range=(dt_ini_dt, dt_fim_dt)
                )

        except ValueError:
            pedidos = Pedido.objects.none()
    # Apenas aplica o filtro do dia atual se nenhum filtro estiver ativo
    filtros_ativos = any([
        s, f_s, por_dt == 'Sim', cli, tp_dt and tp_dt != 'Todos'
    ])
    if not filtros_ativos:
        pedidos = pedidos.filter(
            dt_emi=hoje,
            situacao='Aberto'
        )

    # Filtro por situação
    if f_s and f_s != 'Todos':
        pedidos = pedidos.filter(situacao=f_s)
    # Filtro por cliente
    cliente_selecionado = None
    if cli:
        cliente_selecionado = Cliente.objects.filter(id=cli, vinc_emp=request.user.empresa).first()
        if cliente_selecionado:
            pedidos = pedidos.filter(cli=cliente_selecionado)
    clientes = Cliente.objects.filter(vinc_emp=request.user.empresa)

   # Filtro por Filial
    filial_selecionada = None
    if fil:
        filial_selecionada = Filial.objects.filter(
            id=fil,
            vinc_emp=request.user.empresa
        ).first()
        if filial_selecionada:
            pedidos = pedidos.filter(vinc_emp=filial_selecionada)

    filiais = Filial.objects.filter(
        vinc_emp=request.user.empresa
    )

    # Paginação
    if reg == 'todos':
        num_pagina = pedidos.count() or 1
    else:
        try:
            num_pagina = int(reg) if int(reg) > 0 else 10
        except ValueError:
            num_pagina = 10
    paginator = Paginator(pedidos, num_pagina)
    page = request.GET.get('page')
    pedidos = paginator.get_page(page)

    return render(request, 'pedidos/lista.html', {
        'pedidos': pedidos,
        's': s,
        'cliente_selecionado': cliente_selecionado,
        'filial_selecionada': filial_selecionada,
        'cli': cli,
        'clientes': clientes,
        'filiais': filiais,
        'dt_ini': dt_ini,
        'dt_fim': dt_fim,
        'p_dt': por_dt,
        'tp_dt': tp_dt,
        'reg': reg,
    })

def pedidos_por_produto(request, produto_id):
    pedidos = PedidoProduto.objects.filter(produto_id=produto_id).select_related('pedido', 'pedido__cliente')

    data = []
    for ep in pedidos:
        pedido = ep.pedido
        data.append({
            'pedido_id': pedido.id,
            'data': pedido.dt_ent.strftime('%d/%m/%Y') if pedido.dt_ent else '',
            'cliente': str(pedido.cli),  # converte para string
            'quantidade': float(ep.quantidade),
            'valor_unitario': Decimal(str(self.produto.vl_prod)),
            'total_pedido': float(pedido.total),  # 👈 total da pedido
        })

    return JsonResponse({'pedidos': data})

@login_required
def add_pedido(request):
    # Verifica se o usuário tem permissão para adicionar pedidos
    if not request.user.has_perm('pedidos.add_pedido'):
        messages.info(request, 'Você não tem permissão para adicionar pedidos.')
        return redirect('/pedidos/lista/')

    # Se a requisição for do tipo POST (formulário enviado)
    if request.method == "POST":
        # Cria uma instância do formulário com os dados enviados
        form = PedidoForm(request.POST)

        # Valida se o formulário está correto
        if form.is_valid():
            # Cria o objeto pedido sem salvar ainda no banco
            pedido = form.save(commit=False)
            pedido.save()  # Salva a pedido no banco

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

            # Percorre os produtos organizados e os adiciona na pedido
            for dados in produtos_dict.values():
                try:
                    # Busca o produto no banco pelo código
                    produto = Produto.objects.get(pk=dados.get("codigo"))
                except Produto.DoesNotExist:
                    # Se não encontrar, mostra aviso e ignora este produto
                    messages.warning(request, f"Produto {dados.get('produto')} não encontrado e foi ignorado.")
                    continue

                # Cria ou atualiza o produto vinculado à pedido
                PedidoProduto.objects.update_or_create(
                    pedido=pedido,
                    produto=produto,
                    defaults={
                        "quantidade": parse_decimal(dados.get("quantidade")),
                        "desc_acres": parse_decimal(dados.get("desc_acres")),
                    },
                )

            # Atualiza o valor total da pedido depois de salvar os produtos
            pedido.total = pedido.atualizar_total()
            pedido.save(update_fields=["total"])

            # Exibe mensagem de sucesso e redireciona para a lista de pedidos
            messages.success(request, f'Pedido gerado com sucesso!')
            return redirect(f'/pedidos/lista/?s={pedido.id}')
        else:
            # Caso o formulário seja inválido, gera mensagens de erro personalizadas
            error_messages = []
            for field in form:
                for error in field.errors:
                    error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")

            # Renderiza novamente a página com os erros
            return render(request, "pedidos/add.html", {
                "form": form,
                'error_messages': error_messages
            })
    else:
        # Se não for POST, apenas cria o formulário vazio
        form = PedidoForm()

    # Renderiza a página com o formulário
    return render(request, "pedidos/add.html", {
        "form": form,
    })


@verifica_alguma_permissao(
    'pedidos.add_pedido',
    'pedidos.change_pedido',
    'pedidos.delete_pedido'
)

@login_required
def att_pedido(request, id):
    # Busca a pedido no banco (ou retorna 404 se não existir)
    pedido = get_object_or_404(Pedido, pk=id)

    # Verifica se o usuário tem permissão de alteração
    if not request.user.has_perm('pedidos.change_pedido'):
        messages.info(request, 'Você não tem permissão para editar pedidos.')
        return redirect('/pedidos/lista/')

    if pedido.situacao == "Faturado" and pedido.situacao == "Cancelado":
        messages.warning(request, f'Pedidos só podem ser editados com Situação em Aberto!')
        return redirect(f'/pedidos/lista/?s={pedido.id}')
    if request.method == "POST":
        # Cria o formulário com os dados enviados e a instância existente
        form = PedidoForm(request.POST, instance=pedido)

        if form.is_valid():
            pedido = form.save(commit=False)
            pedido.save()

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

            # Atualiza os produtos da pedido
            produtos_ids = []
            for dados in produtos_dict.values():
                try:
                    produto = Produto.objects.get(pk=dados.get("codigo"))
                except Produto.DoesNotExist:
                    messages.warning(request, f"Produto {dados.get('produto')} não encontrado e foi ignorado.")
                    continue

                ep, created = PedidoProduto.objects.update_or_create(
                    pedido=pedido,
                    produto=produto,
                    defaults={
                        "quantidade": parse_decimal(dados.get("quantidade")),
                        "desc_acres": parse_decimal(dados.get("desc_acres")),
                    },
                )
                produtos_ids.append(ep.id)

            # Atualiza o total da pedido
            pedido.total = pedido.atualizar_total()
            pedido.save(update_fields=["total"])

            messages.success(request, f'Pedido atualizado com sucesso!')
            return redirect(f'/pedidos/lista/?s={pedido.id}')
        else:
            error_messages = []
            for field in form:
                for error in field.errors:
                    error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, "pedidos/att.html", {
                "form": form,
                "pedido": pedido,
                "error_messages": error_messages
            })
    else:
        # Se não for POST, carrega o formulário com os dados da pedido
        form = PedidoForm(instance=pedido)

    return render(request, "pedidos/att.html", {
        "form": form,
        "pedido": pedido,
        "produtos": pedido.itens.all(),
    })


@login_required
def del_pedido(request, id):
    pedido = get_object_or_404(Pedido, pk=id)

    if not request.user.has_perm('pedidos.delete_pedido'):
        messages.info(request, 'Você não tem permissão para deletar pedidos.')
        return redirect('/pedidos/lista/')

    if pedido.situacao != 'Aberto':
        messages.warning(request, 'Pedidos só podem ser deletados com Situação em <i>Aberto</i>!')
        return redirect(f'/pedidos/lista/?s={pedido.id}')

    pedido.delete()
    messages.success(request, f'Pedido deletado com sucesso!')
    return redirect('/pedidos/lista/')

@require_POST
@login_required
def faturar_pedido(request, id):
    pedido = get_object_or_404(Pedido, pk=id)

    if not request.user.has_perm('pedidos.faturar_pedido'):
        messages.info(request, 'Você não tem permissão para faturar pedidos.')
        return redirect('/pedidos/lista/')

    if request.method == 'POST':  # segurança extra
        if pedido.situacao == 'Aberto':
            pedido.situacao = "Faturado"
            pedido.save()

            # Atualiza estoque e preço dos produtos da pedido
            for item in pedido.itens.all():
                produto = item.produto

                # Atualiza estoque
                produto.estoque_prod = (produto.estoque_prod or 0) - (item.quantidade or 0)

                produto.save(update_fields=["estoque_prod"])

            messages.success(
                request,
                f'Pedido faturado com sucesso!'
            )
        else:
            messages.warning(request, f'Pedido já foi faturado antes.')

        return redirect(f'/pedidos/lista/?s={pedido.id}')

@require_POST
@login_required
def cancelar_pedido(request, id):
    pedido = get_object_or_404(Pedido, pk=id)

    if not request.user.has_perm('pedidos.cancelar_pedido'):
        messages.info(request, 'Você não tem permissão para cancelar pedidos.')
        return redirect('/pedidos/lista/')

    if request.method == 'POST':  # segurança extra
        if pedido.situacao == 'Faturado':
            pedido.situacao = "Cancelado"
            pedido.save()

            # Atualiza estoque e preço dos produtos da pedido
            for item in pedido.itens.all():
                produto = item.produto

                # Atualiza estoque
                produto.estoque_prod = (produto.estoque_prod or 0) + (item.quantidade or 0)

                produto.save(update_fields=["estoque_prod"])

            messages.success(
                request,
                f'Pedido cancelado com sucesso!'
            )
        else:
            messages.warning(request, f'Pedido já foi cancelado antes.')

        return redirect(f'/pedidos/lista/?s={pedido.id}')
