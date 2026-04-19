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
from util.permissoes import verifica_permissao
import json
from decimal import Decimal
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from django.http import HttpResponse
from openpyxl.styles import Font
import ast
import operator as op
from django.db.models import Q
from django.db import DatabaseError, IntegrityError
from django.core.exceptions import ObjectDoesNotExist

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

COLUNAS_OBRIGATORIAS = ["codigo", "descricao", "tipo", "expressao", "ativo",]

@verifica_permissao('regras_produto.view_regraproduto')
@login_required
def baixar_modelo_regras(request):
    colunas = COLUNAS_OBRIGATORIAS
    df = pd.DataFrame(columns=colunas)
    df.loc[0] = ["001", "Descrição exemplo", "QTD", "x > 10", True]
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="modelo_importacao_regras.xlsx"'
    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return response

@verifica_permissao('regras_produto.view_regraproduto')
@login_required
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
        ws.append([regra.codigo, regra.descricao, regra.tipo, regra.expressao, 'Sim' if regra.ativo else 'Não'])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = (f'attachment; filename=regras_produto_{empresa.id}.xlsx')
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
    sit = request.GET.get('sit')
    tipo = request.GET.get('tipo')
    reg = request.GET.get('reg', '10')
    regras = RegraProduto.objects.filter(vinc_emp=empresa)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        regras = regras.filter(descricao__icontains=norm_s).order_by('descricao')
    elif tp == 'cod' and s:
        try:
            regras = regras.filter(codigo__iexact=s).order_by('descricao')
        except ValueError:
            regras = RegraProduto.objects.none()
    if sit == 'ativo':
        regras = regras.filter(ativo=True)
    elif sit == 'inativo':
        regras = regras.filter(ativo=False)
    if tipo == 'qtd':
        regras = regras.filter(tipo='QTD')
    elif tipo == 'selecao':
        regras = regras.filter(tipo='SELECAO')
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
    return render(request, 'regras_produto/lista.html', {'regras': regras, 'form_importacao': form, 's': s, 'tp': tp, 'sit': sit, 'tipo': tipo, 'reg': reg,})

@login_required
def lista_regras_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit():
            condicao_busca = Q(descricao__icontains=termo_busca) | Q(id=termo_busca)
        else:
            condicao_busca = Q(descricao__icontains=termo_busca)
        regras = RegraProduto.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': regra.id, 'text': f"{regra.codigo}", 'descricao': regra.descricao} for regra in regras]
        return JsonResponse({'results': results})
    except Exception as e:
        print(f"Erro na busca AJAX: {e}")
        return JsonResponse({'results': [], 'error': str(e)})

OPERADORES = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.Pow: op.pow, ast.USub: op.neg,}

def avaliar_expressao_segura(expressao, contexto):
    def avaliar(no):
        if isinstance(no, ast.Num):
            return Decimal(str(no.n))
        elif isinstance(no, ast.Constant):  # Python 3.8+
            return Decimal(str(no.value))
        elif isinstance(no, ast.BinOp):
            return OPERADORES[type(no.op)](avaliar(no.left), avaliar(no.right))
        elif isinstance(no, ast.UnaryOp):
            return OPERADORES[type(no.op)](avaliar(no.operand))
        elif isinstance(no, ast.Name):
            if no.id in contexto:
                return Decimal(str(contexto[no.id]))
            raise ValueError(f"Variável não permitida: {no.id}")
        else:
            raise TypeError(f"Operação não permitida: {type(no)}")
    arvore = ast.parse(expressao, mode='eval')
    return avaliar(arvore.body)

@login_required
def regras_js(request):
    empresa = request.user.empresa
    if not empresa:
        return JsonResponse({}, status=403)
    regras = RegraProduto.objects.filter(
        vinc_emp=empresa,
        ativo=True
    ).values('codigo', 'tipo', 'expressao_json')
    data = {
        r['codigo']: {
            'tipo': r['tipo'],
            'expressao_json': r['expressao_json'],
        }
        for r in regras
    }
    return JsonResponse(data)

@require_POST
@login_required
def aplicar_regras_porta(request):
    try:
        corpo = json.loads(request.body)
        if isinstance(corpo, list):
            dados = corpo[0]
        else:
            dados = corpo
        tabela_id = dados.get('tabela_id')
        contexto = dados.get('contexto', {})
        if not tabela_id:
            return JsonResponse({'success': False, 'error': 'Tabela não informada'}, status=400)
        regras = RegraProduto.objects.filter(vinc_emp=request.user.empresa, ativo=True)
        produtos_resultado = []
        for regra in regras:
            produto_selecionado = None
            qtd_calculada = 0
            if regra.tipo == 'SELECAO':
                produto_selecionado, qtd_calculada = aplicar_regra_selecao(regra, contexto)
            if regra.tipo == 'QTD':
                if regra.expressao_json:
                    itens = regra.expressao_json
                    if isinstance(itens, str):
                        itens = json.loads(itens)
                    for item in itens:
                        produto = Produto.objects.filter(id=item.get('produto_id')).first()
                        expr = item.get('qtd_expr')
                        try:
                            qtd = calcular_expressao_segura(expr, contexto)
                        except:
                            qtd = 0
                        if produto and qtd > 0:
                            preco = ProdutoTabela.objects.filter(produto=produto, tabela_id=tabela_id).first()
                            if not preco:
                                continue
                            produtos_resultado.append({'id': produto.id, 'codigo': produto.id, 'desc_prod': produto.desc_prod, 'unidProd': produto.unidProd.nome_unidade if produto.unidProd else '',
                                'tp_prod': produto.tp_prod, 'vl_compra': float(produto.vl_compra), 'vl_unit': float(preco.vl_prod), 'qtd': float(qtd), 'regra_origem': regra.codigo})
                else:
                    produto = regra.produto
                    try:
                        qtd = calcular_expressao_segura(regra.expressao, contexto)
                    except:
                        qtd = 0
                    if produto and qtd > 0:
                        preco = ProdutoTabela.objects.filter(produto=produto, tabela_id=tabela_id).first()
                        if not preco:
                            continue
                        produtos_resultado.append({'id': produto.id, 'codigo': produto.id, 'desc_prod': produto.desc_prod, 'unidProd': produto.unidProd.nome_unidade if produto.unidProd else '',
                            'tp_prod': produto.tp_prod, 'vl_compra': float(produto.vl_compra), 'vl_unit': float(preco.vl_prod), 'qtd': float(qtd), 'regra_origem': regra.codigo})
            if produto_selecionado and qtd_calculada > 0:
                try:
                    preco = ProdutoTabela.objects.filter(produto=produto_selecionado, tabela_id=tabela_id).first()
                    if not preco:
                        continue
                    produtos_resultado.append({'id': produto_selecionado.id, 'codigo': produto_selecionado.id, 'desc_prod': produto_selecionado.desc_prod,
                        'unidProd': str(produto_selecionado.unidProd) if produto_selecionado.unidProd else '', 'tp_prod': produto_selecionado.tp_prod,
                        'vl_compra': float(produto_selecionado.vl_compra), 'vl_unit': float(preco.vl_prod), 'qtd': qtd_calculada, 'regra_origem': regra.codigo})
                except ProdutoTabela.DoesNotExist:
                    print(f"Preço não encontrado para produto {produto_selecionado.id} na tabela {tabela_id}")
                    continue
        produtos_resultado.sort(key=lambda x: x['desc_prod'])
        return JsonResponse({'success': True, 'produtos': produtos_resultado})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def calcular_expressao_segura(expr, contexto):
    def _eval(node):
        if isinstance(node, ast.Num):  # número
            return node.n
        elif isinstance(node, ast.Constant):  # py3.8+
            return node.value
        elif isinstance(node, ast.BinOp):  # operação
            return OPERADORES[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):  # negativo
            return OPERADORES[type(node.op)](_eval(node.operand))
        elif isinstance(node, ast.Name):  # variável
            if node.id in contexto:
                return contexto[node.id]
            raise ValueError(f"Variável '{node.id}' não encontrada")
        else:
            raise TypeError(node)
    tree = ast.parse(expr, mode='eval')
    return _eval(tree.body)

def aplicar_regra_selecao(regra, contexto):
    try:
        if not regra.expressao_json:
            return None, 0
        criterios = regra.expressao_json
        if isinstance(criterios, str):
            criterios = json.loads(criterios)
        if not isinstance(criterios, list):
            return None, 0
    except:
        return None, 0
    for item in criterios:
        condicoes = item.get('condicoes', {})
        atende = True
        for chave, valor in condicoes.items():
            if chave == 'max':
                if contexto.get('peso', 0) > valor:
                    atende = False
                    break
            elif chave == 'valor':
                campo = condicoes.get('campo')
                if not campo or contexto.get(campo) != valor:
                    atende = False
                    break
        if atende:
            produto_id = item.get('produto_id')
            qtd_expr = item.get('qtd_expr')
            produto = Produto.objects.filter(id=produto_id).first()
            qtd = 1
            if qtd_expr:
                try:
                    qtd = calcular_expressao_segura(qtd_expr, contexto)
                except:
                    qtd = 1
            return produto, qtd
    return None, 0

@require_POST
@login_required
def calcular_orcamento(request):
    empresa = request.user.empresa
    try:
        raw_body = json.loads(request.body)
        body = raw_body[0] if isinstance(raw_body, list) else raw_body
        tabela_id = body.get('tabela_id')
        produtos_req = body.get('produtos', [])
        ids_originais = list(set(p['id'] for p in produtos_req if 'id' in p))
        produtos_base = Produto.objects.filter(id__in=ids_originais, vinc_emp=empresa)
        precos = {p.produto_id: p.vl_prod for p in ProdutoTabela.objects.filter(tabela_id=tabela_id,produto_id__in=ids_originais)}
        itens_dict = {}
        total_geral = Decimal('0.00')
        for prod in produtos_base:
            qtd = Decimal('1')
            vl_unit = precos.get(prod.id, Decimal('0.00'))
            total = qtd * vl_unit
            item = itens_dict.setdefault(prod.id, {'id': prod.id,'desc': prod.desc_prod,'qtd': Decimal('0'),'vl_unit': vl_unit,'total': Decimal('0.00'),'regra_aplicada': None})
            item['qtd'] += qtd
            item['total'] += total
        itens_saida = []
        for item in itens_dict.values():
            total_geral += item['total']
            itens_saida.append({'id': item['id'],'desc': item['desc'],'qtd': float(item['qtd']),'vl_unit': float(item['vl_unit']),'total': float(item['total']),'regra_aplicada': item['regra_aplicada']})
        return JsonResponse({'itens': itens_saida, 'total': float(total_geral)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def add_regra(request):
    error_messages = []
    if not request.user.has_perm('regras_produto.add_regraproduto'):
        messages.info(request, 'Você não tem permissão para adicionar regras de produto.')
        return redirect('/regras_produto/lista/')
    empresa = request.user.empresa
    try:
        if request.method == 'POST':
            expressao_json = request.POST.get('expressao_json')
            form = RegraProdutoForm(request.POST, empresa=empresa)
            if not form.is_valid():
                erros = [
                    f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!"
                    for field in form if field.errors
                ]
                return render(request, "regras_produto/att.html", {"form": form, "e": e, "error_messages": erros})
            
            e = form.save(commit=False)
            e.vinc_emp = empresa
            try:
                parsed = json.loads(expressao_json) if expressao_json else []
                e.expressao_json = parsed
            except:
                e.expressao_json = []
            e.save()
            messages.success(request, 'Regra adicionada com sucesso!')
            est = str(e.codigo)
            return redirect('/regras_produto/lista/?tp=cod&s=' + est)
    except ObjectDoesNotExist: error_messages.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {str(e)}")
    except DatabaseError as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco de dados: {str(e)}")
    except Exception as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")        
    form = RegraProdutoForm(empresa=empresa)
    return render(request, 'regras_produto/add.html', {'form': form})

@login_required
def att_regra(request, id):
    error_messages = []
    empresa = request.user.empresa
    e = get_object_or_404(RegraProduto, pk=id, vinc_emp=empresa)
    expressao_json_str = json.dumps(e.expressao_json or [])
    form = RegraProdutoForm(instance=e, empresa=empresa)
    if not request.user.has_perm('regras_produto.change_regraproduto'):
        messages.info(request, 'Você não tem permissão para editar regras de produto.')
        return redirect('/regras_produto/lista/')
    try:
        if request.method == 'POST':
            expressao_json = request.POST.get('expressao_json')
            form = RegraProdutoForm(request.POST, instance=e, empresa=empresa)
            if not form.is_valid():
                erros = [
                    f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!"
                    for field in form if field.errors
                ]
                return render(request, "regras_produto/att.html", {"form": form, "e": e, "error_messages": erros, "expressao_json_str": expressao_json_str})
            e = form.save(commit=False)
            e.vinc_emp = empresa
            try:
                parsed = json.loads(expressao_json) if expressao_json else []
                e.expressao_json = parsed
            except:
                e.expressao_json = []
            e.save()
            est = str(e.codigo)
            
            messages.success(request, 'Regra atualizada com sucesso!')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            else:
                return redirect('/regras_produto/lista/?tp=cod&s=' + est)
    except ObjectDoesNotExist: error_messages.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {str(e)}")
    except DatabaseError as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco de dados: {str(e)}")
    except Exception as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return render(request, 'regras_produto/att.html', {'form': form, 'error_messages': error_messages, 'expressao_json_str': expressao_json_str})

@login_required
def del_regra(request, id):
    if not request.user.has_perm('regras_produto.delete_regraproduto'):
        messages.info(request, 'Você não tem permissão para deletar regras de produto.')
        return redirect('/regras_produto/lista/')
    e = get_object_or_404(RegraProduto, pk=id, vinc_emp=request.user.empresa)
    e.delete()
    messages.success(request, 'Regra deletada com sucesso!')
    return redirect('/regras_produto/lista/')