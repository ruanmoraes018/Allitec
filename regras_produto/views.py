import re
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import pandas as pd
from django.db import transaction
from produtos.models import Produto, ProdutoTabela
from .models import RegraProduto, RegraProdutoItem, CondicaoRegraProduto
from .forms import RegraProdutoForm, ImportarRegraProdutoForm, RegraProdutoItemForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
import json
from decimal import Decimal, InvalidOperation
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from django.http import HttpResponse
from openpyxl.styles import Font
import ast
import operator as op
from django.db.models import Q
from django.db import DatabaseError, IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from util.parse_decimal import parse_decimal
from util.logs import gerar_alteracoes, registrar_log
from decimal import ROUND_UP
from django.forms import inlineformset_factory

ItemFormSet = inlineformset_factory(RegraProduto, RegraProdutoItem, form=RegraProdutoItemForm, extra=0, can_delete=True)

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

COLUNAS_OBRIGATORIAS = ["codigo", "descricao", "tipo", "expressao_json", "ativo",]

@verifica_permissao('regras_produto.view_regraproduto')
@login_required
def baixar_modelo_regras(request):
    colunas = COLUNAS_OBRIGATORIAS
    df = pd.DataFrame(columns=colunas)
    df.loc[0] = ["001", "Descrição exemplo", "QTD", "x > 10", True]
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="Modelo Importação Regras de Produto.xlsx"'
    with pd.ExcelWriter(response, engine='xlsxwriter') as writer: df.to_excel(writer, index=False)
    return response

@verifica_permissao('regras_produto.view_regraproduto')
@login_required
def exportar_regras_produto(request):
    empresa = request.user.empresa
    wb = Workbook()
    ws = wb.active
    ws.title = 'regras_produto'
    # Cabeçalho IGUAL à planilha matriz
    headers = ['codigo', 'descricao', 'tipo', 'expressao_json', 'ativo']
    ws.append(headers)
    # Negrito na primeira linha
    bold_font = Font(bold=True)
    for col in range(1, len(headers) + 1):
        ws.cell(row=1, column=col).font = bold_font
    regras = RegraProduto.objects.filter(vinc_emp=empresa).order_by('cod_local')
    for regra in regras:
        ws.append([regra.codigo, regra.descricao, regra.tipo, json.dumps(regra.expressao_json, ensure_ascii=False) if regra.expressao_json else '', 'Sim' if regra.ativo else 'Não'])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = (f'attachment; filename=Regras de Produto {empresa.id}.xlsx')
    wb.save(response)
    return response

@verifica_permissao('regras_produto.view_regraproduto')
@login_required
@transaction.atomic
def lista_regras(request):
    empresa = request.user.empresa
    if request.method == "POST":
        form = ImportarRegraProdutoForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo = form.cleaned_data["arquivo"]
            try: df = pd.read_excel(arquivo)
            except Exception:
                messages.error(request, "Erro ao ler o arquivo Excel. Tente novamente a importação.")
                return redirect("lista-regras")
            colunas_faltando = [col for col in COLUNAS_OBRIGATORIAS if col not in df.columns]
            if colunas_faltando:
                messages.error(request, f"Colunas obrigatórias ausentes: {', '.join(colunas_faltando)}.")
                return redirect("lista-regras")
            erros = []
            for idx, row in df.iterrows():
                linha = idx + 2
                for col in COLUNAS_OBRIGATORIAS:
                    if pd.isna(row[col]) or str(row[col]).strip() == "":
                        erros.append(f"Linha {linha}: coluna '{col}' está vazia.")
                if row["tipo"] not in ["QTD", "SELECAO"]: erros.append(f"Linha {linha}: tipo inválido ({row['tipo']}).")
            if erros:
                for erro in erros:
                    messages.error(request, erro)
                return redirect("lista-regras")
            for _, row in df.iterrows():
                RegraProduto.objects.update_or_create(vinc_emp=empresa, codigo=row["codigo"], defaults={"descricao": row["descricao"], "tipo": row["tipo"], "expressao_json": row["expressao_json"], "ativo": bool(row["ativo"]),})
            messages.success(request, "Regras de produto importadas com sucesso!")
            return redirect("lista-regras")
    form = ImportarRegraProdutoForm()
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    sit = request.GET.get('sit')
    tipo = request.GET.get('tipo')
    reg = request.GET.get('reg', '10')
    regras = RegraProduto.objects.filter(vinc_emp=empresa)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        regras = regras.filter(descricao__icontains=norm_s).order_by('descricao')
    elif tp == 'cod' and s:
        try: regras = regras.filter(codigo__iexact=s).order_by('descricao')
        except ValueError: regras = RegraProduto.objects.none()
    if sit == 'ativo': regras = regras.filter(ativo=True)
    elif sit == 'inativo': regras = regras.filter(ativo=False)
    if tipo == 'qtd': regras = regras.filter(tipo='QTD')
    elif tipo == 'selecao': regras = regras.filter(tipo='SELECAO')
    if reg == 'todos': num_pagina = regras.count() or 1
    else:
        try: num_pagina = int(reg) if int(reg) > 0 else 10
        except ValueError: num_pagina = 10
    paginator = Paginator(regras, num_pagina)
    page = request.GET.get('page')
    regras = paginator.get_page(page)
    return render(request, 'regras_produto/lista.html', {'regras': regras, 'form_importacao': form, 's': s, 'tp': tp, 'sit': sit, 'tipo': tipo, 'reg': reg,})

@login_required
def lista_regras_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit(): condicao_busca = Q(descricao__icontains=termo_busca) | Q(cod_local=termo_busca)
        else: condicao_busca = Q(descricao__icontains=termo_busca)
        regras = RegraProduto.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': regra.cod_local, 'text': f"{regra.codigo}", 'descricao': regra.descricao} for regra in regras]
        return JsonResponse({'results': results})
    except Exception as e: return JsonResponse({'results': [], 'error': str(e)})

from django.db.models import Prefetch

@login_required
def regras_js(request):
    empresa = request.user.empresa
    if not empresa:
        return JsonResponse({}, status=403)
    regras = (
        RegraProduto.objects.filter(vinc_emp=empresa, ativo=True).prefetch_related(Prefetch("itens", queryset=RegraProdutoItem.objects.prefetch_related("condicoes")))
    )
    data = {}
    for regra in regras:
        data[regra.codigo] = {
            "tipo": regra.tipo, "categoria": regra.categoria, "formula": regra.formula,
            "itens": [
                {
                    "produto": item.produto_id, "formula_qtd": item.formula_qtd, "descricao": item.descricao, "prioridade": item.prioridade,
                    "condicoes": [
                        {"campo": c.campo, "operador": c.operador, "valor": c.valor, "ordem": c.ordem,} for c in item.condicoes.all()
                    ],
                }
                for item in regra.itens.all()
            ],
        }
    return JsonResponse(data)

OPERADORES = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.Pow: op.pow, ast.USub: op.neg,}
import traceback

def avaliar_expressao_segura(expressao, contexto):
    def avaliar(no):
        if isinstance(no, ast.Num): return Decimal(str(no.n))
        elif isinstance(no, ast.Constant): return Decimal(str(no.value))
        elif isinstance(no, ast.BinOp): return OPERADORES[type(no.op)](avaliar(no.left), avaliar(no.right))
        elif isinstance(no, ast.UnaryOp): return OPERADORES[type(no.op)](avaliar(no.operand))
        elif isinstance(no, ast.Name):
            if no.id in contexto: return Decimal(str(contexto[no.id]))
            raise ValueError(f"Variável não permitida: {no.id}")
        else: raise TypeError(f"Operação não permitida: {type(no)}")
    arvore = ast.parse(expressao, mode='eval')
    return avaliar(arvore.body)

def calcular_expressao_segura(expr, contexto):
    def _eval(node):
        if isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            return OPERADORES[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            return OPERADORES[type(node.op)](_eval(node.operand))
        elif isinstance(node, ast.Name):
            if node.id in contexto:
                return float(parse_decimal(contexto[node.id]))
            raise ValueError(f"Variável '{node.id}' não encontrada")
        else:
            raise TypeError(node)
    tree = ast.parse(expr, mode='eval')
    return _eval(tree.body)

import re

def _avaliar_condicoes(condicoes, contexto):

    def eh_numero(v):
        # Aceita apenas strings que parecem números: "1.5", "1,5", "10", "-3"
        return bool(re.match(r'^-?\d+([.,]\d+)?$', str(v).strip()))

    for c in condicoes:
        campo = c.campo
        operador = c.operador
        valor_cond = c.valor
        valor_ctx = contexto.get(campo)

        if valor_ctx is None:
            return False

        if eh_numero(valor_ctx) and eh_numero(valor_cond):
            v_ctx  = parse_decimal(str(valor_ctx))
            v_cond = parse_decimal(str(valor_cond))
            if operador == "=":
                if v_ctx != v_cond: return False
            elif operador == ">":
                if not (v_ctx > v_cond): return False
            elif operador == "<":
                if not (v_ctx < v_cond): return False
            elif operador == ">=":
                if not (v_ctx >= v_cond): return False
            elif operador == "<=":
                if not (v_ctx <= v_cond): return False
        else:
            # Comparação string
            v_ctx  = str(valor_ctx).strip().lower()
            v_cond = str(valor_cond).strip().lower()
            if operador == "=":
                if v_ctx != v_cond: return False
            elif operador == "IN":
                lista = valor_cond if isinstance(valor_cond, list) else [valor_cond]
                if v_ctx not in [str(x).strip().lower() for x in lista]:
                    return False
            elif operador in (">", "<", ">=", "<="):
                # strings não suportam esses operadores
                return False

    return True

def aplicar_regra_selecao(regra, contexto):
    for item in regra.itens.prefetch_related("condicoes").all().order_by('prioridade'):  # ← prioridade, não ordem
        condicoes = list(item.condicoes.all())
        print(f'Testando item: {item.produto} | condições: {[(c.campo, c.operador, c.valor) for c in condicoes]}')
        if condicoes and not _avaliar_condicoes(condicoes, contexto):
            continue
        try:
            qtd = calcular_expressao_segura(item.formula_qtd or "1", contexto)
            print(f'QTD calculada para {item.produto}: {qtd}')
        except Exception as e:
            print(f'ERRO na fórmula de {item.produto}: {e}')
            qtd = 1
        return item.produto, qtd, item.descricao
    return None, 0, None

def aplicar_regra_calculo(regra, contexto):
    resultado = []
    for item in regra.itens.prefetch_related("condicoes").all():
        condicoes = list(item.condicoes.all())
        if condicoes and not _avaliar_condicoes(condicoes, contexto):
            continue
        try:
            qtd = calcular_expressao_segura(item.formula_qtd or "1", contexto)
        except Exception:
            qtd = 0
        if qtd > 0:
            resultado.append((item.produto, qtd, item.descricao))
    return resultado

@require_POST
@login_required
def aplicar_regras_porta(request):
    try:
        corpo = json.loads(request.body)
        dados = corpo[0] if isinstance(corpo, list) else corpo
        tabela_id = dados.get('tabela_id')
        contexto = dados.get('contexto', {})
        print('CONTEXTO tipo_lamina:', contexto.get('tipo_lamina'))
        print('CONTEXTO completo:', contexto)
        if not tabela_id:
            return JsonResponse({'success': False, 'error': 'Tabela não informada'}, status=400)
        regras = (RegraProduto.objects.filter(vinc_emp=request.user.empresa, ativo=True).prefetch_related("itens__condicoes", "itens__produto"))
        produtos_resultado = []
        for regra in regras:
            if regra.categoria == 'pintura' and not contexto.get('tem_pintura'):
                continue
            # Dentro do loop for regra in regras, no bloco SELECAO:
            if regra.tipo == 'SELECAO':
                produto, qtd, descricao = aplicar_regra_selecao(regra, contexto)
                if produto and qtd > 0:
                    preco = ProdutoTabela.objects.filter(produto=produto, tabela__codigo=tabela_id).first()
                    if not preco:
                        continue
                    item_resultado = {
                        'id': produto.codigo, 'codigo': produto.codigo, 'desc_prod': produto.desc_prod, 'desc_prod_regra': descricao,
                        'unidProd': str(produto.unidProd) if produto.unidProd else '', 'tp_prod': produto.tp_prod, 'vl_compra': float(produto.vl_compra),
                        'vl_unit': float(preco.vl_prod), 'qtd': float(qtd), 'regra_origem': regra.codigo,
                        # ✅ ADICIONE:
                        'especifico': getattr(produto, 'especifico', None), 'espessura_lam': float(produto.espessura_lam) if getattr(produto, 'espessura_lam', None) else None,
                        'peso_m2': float(produto.peso_m2) if getattr(produto, 'peso_m2', None) else None,
                        'diametro_eixo': float(produto.diametro_eixo) if getattr(produto, 'diametro_eixo', None) else None,
                    }
                    # Se for regra de testeira, marca para o JS capturar
                    if regra.categoria == 'testeira':
                        item_resultado['is_testeira'] = True
                        item_resultado['tamanho_testeira'] = float(produto.tamanho_testeira) if hasattr(produto, 'tamanho_testeira') else None
                    produtos_resultado.append(item_resultado)
            elif regra.tipo in ('CALCULO', 'QTD'):
                for produto, qtd, descricao in aplicar_regra_calculo(regra, contexto):
                    preco = ProdutoTabela.objects.filter(produto=produto, tabela__codigo=tabela_id).first()
                    if not preco:
                        continue
                    produtos_resultado.append({
                        'id': produto.codigo, 'codigo': produto.codigo, 'desc_prod': produto.desc_prod, 'desc_prod_regra': descricao,
                        'unidProd': produto.unidProd.nome_unidade if produto.unidProd else '', 'tp_prod': produto.tp_prod, 'vl_compra': float(produto.vl_compra),
                        'vl_unit': float(preco.vl_prod), 'qtd': float(qtd), 'regra_origem': regra.codigo,
                        # ✅ ADICIONE:
                        'especifico': getattr(produto, 'especifico', None), 'espessura_lam': float(produto.espessura_lam) if getattr(produto, 'espessura_lam', None) else None,
                        'peso_m2': float(produto.peso_m2) if getattr(produto, 'peso_m2', None) else None,
                        'diametro_eixo': float(produto.diametro_eixo) if getattr(produto, 'diametro_eixo', None) else None,
                    })
        produtos_resultado.sort(key=lambda x: x['desc_prod'])
        contexto_derivado = _calcular_campos_derivados(produtos_resultado, contexto)
        return JsonResponse({'success': True, 'produtos': produtos_resultado, 'campos_derivados': contexto_derivado,})
    except Exception:
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'error': traceback.format_exc()}, status=500)

def _calcular_campos_derivados(produtos_resultado, contexto):
    from regras_produto.models import RegraProduto
    alt_c   = Decimal(str(contexto.get("alt_c") or 0))
    qtd_lam = Decimal(str(contexto.get("qtd_lam") or 0))
    larg_c  = Decimal(str(contexto.get("larg_c") or 0))
    # Busca motor selecionado
    motor_item = next((p for p in produtos_resultado if p.get("regra_origem") == "MOTOR_PESO"), None)
    testeira = 32  # fallback
    if motor_item:
        try:
            regra_motor = RegraProduto.objects.get(codigo="MOTOR_PESO")
            tabela_testeiras = (regra_motor.formula or {}).get("testeiras", {})
            desc = (motor_item.get("desc_prod_regra") or motor_item.get("desc_prod") or "").upper()
            for chave, valor in tabela_testeiras.items():
                if chave.upper() in desc:
                    testeira = valor
                    break
        except Exception:
            pass
    return {"qtd_pares_trava": int((qtd_lam / 2).quantize(Decimal("1"), rounding=ROUND_UP)),
        "cortes": {
            "guia": float((alt_c + Decimal("0.05")).quantize(Decimal("0.001"))), "eixo": float(larg_c.quantize(Decimal("0.001"))),
            "soleira": float(larg_c.quantize(Decimal("0.001"))), "tubo": float((alt_c + Decimal("0.20")).quantize(Decimal("0.001"))),
            "perfil": float((alt_c + Decimal("0.10")).quantize(Decimal("0.001"))),
        },
    }

@require_POST
@login_required
def calcular_orcamento(request):
    empresa = request.user.empresa
    try:
        raw_body = json.loads(request.body)
        body = raw_body[0] if isinstance(raw_body, list) else raw_body
        tabela_id    = body.get('tabela_id')
        produtos_req = body.get('produtos', [])
        ids_originais = list(set(p['id'] for p in produtos_req if 'id' in p))
        produtos_base = Produto.objects.filter(codigo__in=ids_originais, vinc_emp=empresa)
        precos = {p.produto.codigo: p.vl_prod for p in ProdutoTabela.objects.filter(tabela__codigo=tabela_id, produto__codigo__in=ids_originais)}
        qtd_por_id = {p['id']: p.get('qtd', 1) for p in produtos_req}
        itens_dict = {}
        total_geral = Decimal('0.00')
        for prod in produtos_base:
            qtd     = parse_decimal(qtd_por_id.get(prod.codigo, 1))
            vl_unit = precos.get(prod.codigo, Decimal('0.00'))
            total   = qtd * vl_unit
            item = itens_dict.setdefault(prod.codigo, {
                'id': prod.codigo, 'desc': prod.desc_prod, 'qtd': Decimal('0'), 'vl_unit': vl_unit, 'total': Decimal('0.00'), 'regra_aplicada': None,
                # Atributos técnicos do produto enviados ao JS
                'especifico': getattr(prod, 'especifico', None), 'espessura_lam': float(getattr(prod, 'espessura_lam', 0) or 0),
                'peso_m2': float(getattr(prod, 'peso_m2', 0) or 0), 'diametro_eixo': float(getattr(prod, 'diametro_eixo', 0) or 0),
            })
            item['qtd']   += qtd
            item['total'] += total
        itens_saida = []
        for item in itens_dict.values():
            total_geral += item['total']
            itens_saida.append({
                'id': item['id'], 'desc': item['desc'], 'qtd': float(item['qtd']), 'vl_unit': float(item['vl_unit']), 'total': float(item['total']),
                'regra_aplicada': item['regra_aplicada'], 'especifico': item['especifico'], 'espessura_lam': item['espessura_lam'], 'peso_m2': item['peso_m2'],
                'diametro_eixo': item['diametro_eixo'],
            })
        return JsonResponse({'itens': itens_saida, 'total': float(total_geral)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

import json
from django.db import IntegrityError, DatabaseError, transaction
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import RegraProduto, RegraProdutoItem, CondicaoRegraProduto
from produtos.models import Produto

def salvar_condicoes_item(item, condicoes_json_str):
    item.condicoes.all().delete()
    if not condicoes_json_str:
        return
    try:
        condicoes = json.loads(condicoes_json_str)
    except (ValueError, TypeError):
        return
    for cond in condicoes:
        campo = cond.get("campo", "").strip()
        operador = cond.get("operador", "").strip()
        valor = cond.get("valor")
        ordem = cond.get("ordem", 0)
        if campo and operador and valor is not None:
            CondicaoRegraProduto.objects.create(regra=item.regra, item=item, campo=campo, operador=operador, valor=valor, ordem=ordem,)

@login_required
def add_regra(request):
    empresa = request.user.empresa
    if request.method == "POST":
        form = RegraProdutoForm(request.POST, empresa=empresa)
        if form.is_valid():
            try:
                with transaction.atomic():
                    regra = form.save(commit=False)
                    regra.vinc_emp = empresa
                    regra.save()
                    itens_formset = ItemFormSet(request.POST, instance=regra, prefix='itens', form_kwargs={'empresa': empresa})
                    if itens_formset.is_valid():
                        instances = itens_formset.save()
                        for idx, item_instance in enumerate(instances):
                            cond_json = request.POST.get(f"itens-{idx}-condicoes_json", '')
                            salvar_condicoes_item(item_instance, cond_json)
                    else:
                        raise Exception(itens_formset.errors)
                registrar_log(request, "CRIAR", "Regra de Produto", regra.descricao,
                    f"Adicionou a regra: {regra.cod_local} - {regra.descricao}",
                    regra.id, gerar_alteracoes(obj_novo=regra)
                )
                messages.success(request, "Regra adicionada com sucesso!")
                return redirect('/regras_produto/lista/?tp=cod&s=' + regra.codigo)
            except Exception as e:
                traceback.print_exc()
                messages.error(request, str(e))
    else:
        form = RegraProdutoForm(empresa=empresa)
        itens_formset = ItemFormSet(prefix='itens', form_kwargs={'empresa': empresa})
    if request.method == "POST" and not form.is_valid():
        itens_formset = ItemFormSet(request.POST, prefix='itens', form_kwargs={'empresa': empresa})
    return render(request, "regras_produto/add.html", {"form": form, "itens_formset": itens_formset,})


@login_required
def att_regra(request, cod_local):
    empresa = request.user.empresa
    if not request.user.has_perm('regras_produto.change_regraproduto'):
        messages.info(request, 'Você não tem permissão para editar regras de produto.')
        return redirect('/regras_produto/lista/')
    regra = get_object_or_404(RegraProduto, cod_local=cod_local, vinc_emp=empresa)
    it_old = RegraProduto.objects.get(cod_local=regra.cod_local, vinc_emp=empresa)
    if request.method == "POST":
        form = RegraProdutoForm(request.POST, instance=regra, empresa=empresa)
        itens_formset = ItemFormSet(request.POST, instance=regra, prefix='itens', form_kwargs={'empresa': request.user.empresa})
        if form.is_valid():
            try:
                with transaction.atomic():
                    regra = form.save()
                    if itens_formset.is_valid():
                        objs = itens_formset.save(commit=False)
                        print("REGRA:", regra.id)
                        for obj in objs:
                            print("ANTES:", obj.regra_id)
                            obj.regra = regra
                            print("DEPOIS:", obj.regra_id)
                            obj.save()
                        for obj in itens_formset.deleted_objects:
                            obj.delete()
                        itens_formset.save_m2m()
                        instances = objs
                        for idx, item_instance in enumerate(instances):
                            cond_json = request.POST.get(f"itens-{idx}-condicoes_json", '')
                            salvar_condicoes_item(item_instance, cond_json)
                    else:
                        raise Exception(itens_formset.errors)
                registrar_log(request, "ALTERAR", "Regra de Produto", regra.descricao,
                    f"Alterou a regra: {regra.cod_local} - {regra.descricao}",
                    regra.id, gerar_alteracoes(it_old, regra)
                )
                messages.success(request, "Regra atualizada com sucesso!")
                next_url = request.POST.get("next") or request.GET.get("next")
                if next_url:
                    return redirect(next_url)
                return redirect('/regras_produto/lista/?tp=cod&s=' + regra.codigo)
            except Exception as e:
                traceback.print_exc()
                messages.error(request, str(e))
            except DatabaseError as e:
                messages.error(request, f"Erro de banco de dados ao atualizar a regra: {e}")
            except Exception as e:
                messages.error(request, f"Erro inesperado ao atualizar a regra: {e}")
        else:
            for field in form:
                for erro in field.errors:
                    messages.error(request, f"Campo '{field.label}': {erro}")
            for erro in form.non_field_errors():
                messages.error(request, erro)
            for i, item_form in enumerate(itens_formset):
                for field in item_form:
                    for erro in field.errors:
                        messages.error(request, f"Item {i+1} — '{field.label}': {erro}")
    else:
        form = RegraProdutoForm(instance=regra, empresa=empresa)
        itens_formset = ItemFormSet(instance=regra, prefix='itens', form_kwargs={'empresa': empresa})
    if request.method == "POST" and not form.is_valid():
        itens_formset = ItemFormSet(request.POST,
            prefix='itens',
            form_kwargs={'empresa': empresa}
        )
    dados = []
    for item in regra.itens.all():
        linha = {"produto_id": item.produto.codigo, "desc_prod": str(item.produto), "qtd_expr": item.formula_qtd}
        cond = {}
        for c in item.condicoes.all():  # ← corrigido: era regra.condicoes, mas CondicaoRegraProduto tem FK pro item
            cond[c.campo] = c.valor
        if cond:
            linha["condicoes"] = cond
        dados.append(linha)
    return render(request, "regras_produto/att.html", {
        "form": form,
        "itens_formset": itens_formset,
    })

@login_required
def del_regra(request, cod_local):
    if not request.user.has_perm('regras_produto.delete_regraproduto'):
        messages.info(request, 'Você não tem permissão para deletar regras de produto.')
        return redirect('/regras_produto/lista/')
    e = get_object_or_404(RegraProduto, cod_local=cod_local, vinc_emp=request.user.empresa)
    registrar_log(
        request, "EXCLUIR", "Regra de Produto", e.descricao,
        f"Excluiu a regra de produto: {e.cod_local} - {e.descricao}",
        e.id, gerar_alteracoes(obj_antigo=e)
    )
    e.delete()
    messages.success(request, 'Regra deletada com sucesso!')
    return redirect('/regras_produto/lista/')