from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import pandas as pd
from django.db import transaction
from produtos.models import Produto, ProdutoTabela
from .models import RegraProduto
from .forms import RegraProdutoForm, ImportarRegraProdutoForm
import unicodedata
from django.http import JsonResponse
from filiais.models import Usuario
from util.permissoes import verifica_permissao
import json
from decimal import Decimal
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from django.http import HttpResponse
from openpyxl.styles import Font
import ast
import operator as op

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

def exportar_regras_produto(request):
    empresa = request.user.empresa

    wb = Workbook()
    ws = wb.active
    ws.title = 'regras_produto'

    # Cabeçalho IGUAL à planilha matriz
    headers = ['codigo', 'descricao', 'tipo', 'expressao', 'ativo']
    ws.append(headers)

    # Negrito na primeira linha
    bold_font = Font(bold=True)

    for col in range(1, len(headers) + 1):
        ws.cell(row=1, column=col).font = bold_font

    regras = RegraProduto.objects.filter(vinc_emp=empresa).order_by('id')

    for regra in regras:
        ws.append([
            regra.codigo,
            regra.descricao,
            regra.tipo,               # QTD ou SELECAO
            regra.expressao,
            'Sim' if regra.ativo else 'Não'
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = (
        f'attachment; filename=regras_produto_{empresa.id}.xlsx'
    )

    wb.save(response)
    return response

COLUNAS_OBRIGATORIAS = [
    "codigo",
    "descricao",
    "tipo",
    "expressao",
    "ativo",
]


@verifica_permissao('regras_produto.view_regraproduto')
@login_required
@transaction.atomic
def lista_regras(request):
    if request.method == "POST":
        form = ImportarRegraProdutoForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo = form.cleaned_data["arquivo"]
            try:
                df = pd.read_excel(arquivo)
            except Exception:
                messages.error(request, "Erro ao ler o arquivo Excel. Tente novamente a importação.")
                return redirect("lista-regras")
            colunas_faltando = [
                col for col in COLUNAS_OBRIGATORIAS if col not in df.columns
            ]
            if colunas_faltando:
                messages.error(request, f"Colunas obrigatórias ausentes: {', '.join(colunas_faltando)}.")
                return redirect("lista-regras")
            erros = []
            for idx, row in df.iterrows():
                linha = idx + 2
                for col in COLUNAS_OBRIGATORIAS:
                    if pd.isna(row[col]) or str(row[col]).strip() == "":
                        erros.append(
                            f"Linha {linha}: coluna '{col}' está vazia."
                        )
                if row["tipo"] not in ["QTD", "SELECAO"]:
                    erros.append(f"Linha {linha}: tipo inválido ({row['tipo']}).")
            if erros:
                for erro in erros:
                    messages.error(request, erro)
                return redirect("lista-regras")
            empresa = request.user.empresa
            for _, row in df.iterrows():
                RegraProduto.objects.update_or_create(
                    vinc_emp=empresa,
                    codigo=row["codigo"],
                    defaults={"descricao": row["descricao"], "tipo": row["tipo"], "expressao": row["expressao"], "ativo": bool(row["ativo"]),}
                )
            messages.success(request, "Regras de produto importadas com sucesso!")
            return redirect("lista-regras")
    form = ImportarRegraProdutoForm()
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')
    regras = RegraProduto.objects.filter(vinc_emp=request.user.empresa)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        regras = regras.filter(descricao__icontains=norm_s).order_by('descricao')
    elif tp == 'cod' and s:
        try:
            regras = regras.filter(id__iexact=s).order_by('descricao')
        except ValueError:
            regras = RegraProduto.objects.none()
    if reg == 'todos':
        num_pagina = regras.count() or 1
    else:
        try:
            num_pagina = int(reg) if int(reg) > 0 else 10
        except ValueError:
            num_pagina = 10
    paginator = Paginator(regras, num_pagina)
    page = request.GET.get('page')
    regras = paginator.get_page(page)
    return render(request, 'regras_produto/lista.html', {'regras': regras, 'form_importacao': form, 's': s, 'tp': tp, 'reg': reg,})

@login_required
def lista_regras_ajax(request):
    term = request.GET.get('term', '')
    regras = RegraProduto.objects.filter(descricao__icontains=term)[:50]
    data = {
        'regras': [
            {
                'id': regra.id,
                'codigo': regra.codigo,
                'descricao': regra.descricao
            }
            for regra in regras
        ]
    }
    return JsonResponse(data)

OPERADORES = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.USub: op.neg,
}

def avaliar_expressao_segura(expressao, contexto):
    def avaliar(no):
        if isinstance(no, ast.Num):
            return Decimal(str(no.n))

        elif isinstance(no, ast.Constant):  # Python 3.8+
            return Decimal(str(no.value))

        elif isinstance(no, ast.BinOp):
            return OPERADORES[type(no.op)](
                avaliar(no.left),
                avaliar(no.right)
            )

        elif isinstance(no, ast.UnaryOp):
            return OPERADORES[type(no.op)](
                avaliar(no.operand)
            )

        elif isinstance(no, ast.Name):
            if no.id in contexto:
                return Decimal(str(contexto[no.id]))
            raise ValueError(f"Variável não permitida: {no.id}")

        else:
            raise TypeError(f"Operação não permitida: {type(no)}")

    arvore = ast.parse(expressao, mode='eval')
    return avaliar(arvore.body)


# ================================
# REGRAS JS (continua igual)
# ================================

@login_required
def regras_js(request):
    empresa = request.user.empresa
    if not empresa:
        return JsonResponse({}, status=403)

    regras = RegraProduto.objects.filter(
        vinc_emp=empresa,
        ativo=True
    ).values('codigo', 'tipo', 'expressao')

    data = {
        r['codigo']: {
            'tipo': r['tipo'],
            'expressao': r['expressao'],
        }
        for r in regras
    }

    return JsonResponse(data)


# ================================
# REGRA DE SELEÇÃO (sem eval)
# ================================

def aplicar_regra_selecao(regra, contexto):
    """
    Retorna o NOME do produto selecionado
    """
    dados = json.loads(regra.expressao)

    # ======== MOTOR (por peso) ========
    if isinstance(dados, list):
        peso = Decimal(str(contexto.get('peso', 0)))

        for item in sorted(dados, key=lambda x: x['max']):
            if peso <= Decimal(str(item['max'])):
                return item['produto']

    # ======== MAPA DIRETO (lamina, pintura etc) ========
    if isinstance(dados, dict):
        for valor in contexto.values():
            if valor in dados:
                return dados[valor]

    return None


# ================================
# CALCULAR ORÇAMENTO (AJUSTADA)
# ================================

@require_POST
@login_required
def calcular_orcamento(request):
    empresa = request.user.empresa
    body = json.loads(request.body)

    tabela_id = body.get('tabela_id')
    contexto = body.get('contexto', {})
    produtos_req = body.get('produtos', [])

    # ==========================
    # CONTEXTO DECIMAL
    # ==========================
    contexto_decimal = {
        k: Decimal(str(v)) for k, v in contexto.items()
    }

    # ==========================
    # REMOVE DUPLICADOS JÁ AQUI
    # ==========================
    ids_produtos = list(set(p['id'] for p in produtos_req if 'id' in p))

    produtos_base = Produto.objects.select_related('regra').filter(
        id__in=ids_produtos,
        vinc_emp=empresa
    )

    # Cache de preços da tabela
    precos_tabela = {}
    if tabela_id:
        itens_tabela = ProdutoTabela.objects.filter(
            tabela_id=tabela_id,
            produto_id__in=ids_produtos
        )
        precos_tabela = {
            item.produto_id: item.vl_prod
            for item in itens_tabela
        }

    itens_dict = {}
    total_geral = Decimal('0.00')

    # ==========================
    # LOOP PRINCIPAL
    # ==========================
    for prod in produtos_base:

        produto_final = prod

        # ======================
        # REGRA DE SELEÇÃO
        # ======================
        if prod.regra and prod.regra.tipo == 'SELECAO':
            produto_nome = aplicar_regra_selecao(prod.regra, contexto_decimal)

            if not produto_nome:
                continue

            produto_final = Produto.objects.filter(
                desc_prod=produto_nome,
                vinc_emp=empresa
            ).select_related('regra').first()

            if not produto_final:
                continue

        # ======================
        # REGRA DE QUANTIDADE
        # ======================
        qtd = Decimal('1')

        if produto_final.regra and produto_final.regra.tipo == 'QTD':
            try:
                qtd = avaliar_expressao_segura(
                    produto_final.regra.expressao,
                    contexto_decimal
                )
            except Exception:
                qtd = Decimal('0')

        if qtd <= 0:
            continue

        # ======================
        # VALOR UNITÁRIO
        # ======================
        vl_unit = precos_tabela.get(produto_final.id, Decimal('0.00'))

        total = qtd * vl_unit

        # ======================
        # AGRUPAMENTO SEGURO
        # ======================
        item = itens_dict.setdefault(produto_final.id, {
            'id': produto_final.id,
            'desc': produto_final.desc_prod,
            'qtd': Decimal('0'),
            'vl_unit': vl_unit,
            'total': Decimal('0.00'),
            'regra_aplicada': produto_final.regra.codigo if produto_final.regra else None
        })

        item['qtd'] += qtd
        item['total'] += total

    # ==========================
    # MONTA LISTA FINAL
    # ==========================
    itens = []

    for item in itens_dict.values():
        total_geral += item['total']

        itens.append({
            'id': item['id'],
            'desc': item['desc'],
            'qtd': float(item['qtd']),
            'vl_unit': float(item['vl_unit']),
            'total': float(item['total']),
            'regra_aplicada': item['regra_aplicada']
        })

    return JsonResponse({
        'itens': itens,
        'total': float(total_geral)
    })

@login_required
def add_regra(request):
    if not request.user.has_perm('regras_produto.add_regraproduto'):
        messages.info(request, 'Você não tem permissão para adicionar regras de produto.')
        return redirect('/regras_produto/lista/')
    if request.method == 'POST':
        form = RegraProdutoForm(request.POST)
        if form.is_valid():
            e = form.save(commit=False)
            if request.user.is_authenticated:
                try:
                    e.vinc_emp = request.user.empresa  # Busca a filial do usuário logado
                except Usuario.DoesNotExist:
                    return JsonResponse({'error': 'Usuário não possui filial vinculada'}, status=400)
            e.save()
            messages.success(request, 'Regra adicionada com sucesso!')
            est = str(e.id)
            return redirect('/regras_produto/lista/?tp=cod&s=' + est)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'regras_produto/add.html', {'form': form, 'error_messages': error_messages})
    else: form = RegraProdutoForm()
    return render(request, 'regras_produto/add.html', {'form': form})

@login_required
def att_regra(request, id):
    e = get_object_or_404(RegraProduto, pk=id)
    form = RegraProdutoForm(instance=e)
    if not request.user.has_perm('regras_produto.change_regraproduto'):
        messages.info(request, 'Você não tem permissão para editar regras de produto.')
        return redirect('/regras_produto/lista/')
    if request.method == 'POST':
        form = RegraProdutoForm(request.POST, instance=e)
        if form.is_valid():
            e.save()
            est = str(e.id)
            messages.success(request, 'Regra atualizada com sucesso!')
            return redirect('/regras_produto/lista/?tp=cod&s=' + est)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'regras_produto/att.html', {'form': form, 'e': e, 'error_messages': error_messages})
    else:
        return render(request, 'regras_produto/att.html', {'form': form, 'e': e})

@login_required
def del_regra(request, id):
    if not request.user.has_perm('regras_produto.delete_regraproduto'):
        messages.info(request, 'Você não tem permissão para deletar regras de produto.')
        return redirect('/regras_produto/lista/')
    e = get_object_or_404(RegraProduto, pk=id)
    e.delete()
    messages.success(request, 'Regra deletada com sucesso!')
    return redirect('/regras_produto/lista/')