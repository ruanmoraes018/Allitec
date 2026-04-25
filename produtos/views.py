from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Produto, ProdutoTabela, CodigoProduto
from .forms import ProdutoForm
import unicodedata
from django.http import JsonResponse, HttpResponseForbidden
from filiais.models import Usuario
from util.permissoes import verifica_permissao
from grupos.models import Grupo
from marcas.models import Marca
from unidades.models import Unidade
from tabelas_preco.models import TabelaPreco
from decimal import Decimal, InvalidOperation
import re
from django.urls import reverse
from django.db import connection, transaction
from django.db.models import Q
from django.db import DatabaseError, IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.http import require_POST
import json

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
    empresa = request.user.empresa
    produtos_qs = Produto.objects.filter(vinc_emp=empresa)
    if ordem == '0': produtos_qs = produtos_qs.order_by('desc_prod')
    elif ordem == '1': produtos_qs = produtos_qs.order_by('id')
    else: produtos_qs = produtos_qs.order_by(ordem)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        produtos_qs = produtos_qs.filter(desc_normalizado__icontains=norm_s)
    elif tp == 'cod':
        if s:
            try: produtos_qs = produtos_qs.filter(id__iexact=s)
            except ValueError:  produtos_qs = Produto.objects.none()
    if tp_produto in ['Principal', 'Adicional']: produtos_qs = produtos_qs.filter(tp_prod__exact=tp_produto)
    if sit == '1': produtos_qs = produtos_qs.filter(situacao='Ativo')
    elif sit == '2': produtos_qs = produtos_qs.filter(situacao='Inativo')
    if grupo: produtos_qs = produtos_qs.filter(grupo_id=grupo)
    if marca: produtos_qs = produtos_qs.filter(marca_id=marca)
    if unid: produtos_qs = produtos_qs.filter(unidProd_id=unid)
    if reg == 'todos':
        num_pagina = produtos_qs.count() or 1
    else:
        try:
            num_pagina = int(reg) if int(reg) > 0 else 10
        except ValueError:
            num_pagina = 10
    paginator = Paginator(produtos_qs, num_pagina)
    page = request.GET.get('page')
    produtos_qs = paginator.get_page(page)
    produtos_ids = [p.id for p in produtos_qs]
    tabelas_map = {}
    if produtos_ids:
        tabelas = (ProdutoTabela.objects.filter(produto_id__in=produtos_ids, produto__vinc_emp=empresa).select_related('tabela'))
        for tab in tabelas:
            tabelas_map.setdefault(tab.produto_id, []).append({"id": tab.id, "descricao": tab.tabela.descricao if tab.tabela else str(tab), "vl_prod": float(tab.vl_prod)})
    for p in produtos_qs:
        p.tab_conv = tabelas_map.get(p.id, [])
    return render(request, 'produtos/lista.html', {'produtos': produtos_qs, 's': s, 'tp': tp, 'sit': sit, 'ordem': ordem, 'marca': marca, 'marcas': Marca.objects.filter(vinc_emp=empresa), 'grupo': grupo, 'grupos': Grupo.objects.filter(vinc_emp=empresa), 'unidades': Unidade.objects.filter(vinc_emp=empresa), 'unid': unid, 'reg': reg, 'tp_produto': tp_produto})

@login_required
def att_prod_lote(request):
    if request.method == "POST":
        produtos_ids = request.POST.getlist('multi')
        switch_grupo = request.POST.get('switchSit')
        switch_unidade = request.POST.get('switchEmp')
        switch_marca = request.POST.get('switchMarca')
        switch_lista_orc = request.POST.get('switchListaOrc')
        switch_situacao = request.POST.get('switchSituacao')
        unidade_id = request.POST.get('unid1')
        grupo_id = request.POST.get('gp1')
        marca_id = request.POST.get('marca1')
        situacao = request.POST.get('situacao1')
        empresa = request.user.empresa
        produtos = Produto.objects.filter(id__in=produtos_ids, vinc_emp=empresa)
        if not produtos.exists():
            messages.info(request, 'Nenhum produto selecionado.')
            return redirect('/produtos/lista/')
        alguma_alteracao = False
        gp = None
        unidade = None
        marca = None
        if switch_grupo == 'on' and grupo_id:
            gp = Grupo.objects.filter(id=grupo_id, vinc_emp=empresa).first()
        if switch_unidade == 'on' and unidade_id:
            unidade = Unidade.objects.filter(id=unidade_id, vinc_emp=empresa).first()
        if switch_marca == 'on' and marca_id:
            marca = Marca.objects.filter(id=marca_id, vinc_emp=empresa).first()
        for produto in produtos:
            if switch_grupo == 'on' and grupo_id and gp:
                produto.grupo = gp
                alguma_alteracao = True
            if switch_unidade == 'on' and unidade_id and unidade:
                produto.unidProd = unidade
                alguma_alteracao = True
            if switch_lista_orc == 'on':
                produto.lista_orc = True
                alguma_alteracao = True
            if switch_marca == 'on' and marca_id and marca:
                produto.marca = marca
                alguma_alteracao = True
            if switch_situacao == 'on' and situacao in ['Ativo', 'Inativo']:
                produto.situacao = situacao
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
            tabela = TabelaPreco.objects.get(id=tabela_id, vinc_emp=request.user.empresa)
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
            try: vl_compra = Decimal(p.vl_compra or '0')
            except InvalidOperation: vl_compra = Decimal('0')
            if tp_atrib == "0":  # ATRIBUIR POR MARGEM
                margem = val_1
                vl_prod = vl_compra * (Decimal('1') + margem / Decimal('100'))
            elif tp_atrib == "1":  # ATRIBUIR POR VALOR
                vl_prod = val_1
                margem = ((vl_prod - vl_compra) / vl_compra * Decimal('100')) if vl_compra > 0 else Decimal('0')
            else:
                messages.warning(request, f"Tipo de atribuição inválido ({tp_atrib}).")
                continue
            ProdutoTabela.objects.update_or_create(produto=p, tabela=tabela, defaults={'vl_prod': vl_prod, 'margem': margem})
            alguma_alteracao = True
        if alguma_alteracao:
            tipo_label = "margem" if tp_atrib == "0" else "valor"
            messages.success(request, f"Tabela de preço atualizada com base em {tipo_label} com sucesso!")
        else: messages.info(request, 'Nenhuma alteração realizada.')
    return redirect('/produtos/lista/')

@login_required
@require_POST
def att_tb_preco_lote(request):
    empresa = request.user.empresa
    try:
        body = json.loads(request.body or '{}')
        tabela_id = body.get('tabela_id')
        tipo = str(body.get('tipo', '')).strip()
        campo_1 = Decimal(str(body.get('campo_1') or 0))
        campo_2 = Decimal(str(body.get('campo_2') or 0))
        produtos_req = body.get('produtos', [])
        if not tabela_id:
            return JsonResponse({'ok': False, 'msg': 'Selecione uma tabela de preço.'})
        if not produtos_req:
            return JsonResponse({'ok': False, 'msg': 'Nenhum produto foi selecionado.'})
        tabela = TabelaPreco.objects.get(id=tabela_id, vinc_emp=empresa)
        valores_ret = {}
        for item in produtos_req:
            pid = item.get('id')
            base_calculo = Decimal(str(item.get('base_calculo') or 0))
            produto = Produto.objects.get(id=pid, vinc_emp=empresa)
            margem = Decimal('0.00')
            valor = Decimal('0.00')
            if tipo == "0":  # margem
                margem = campo_1
                valor = base_calculo * (Decimal('1.00') + (margem / Decimal('100.00')))
            elif tipo == "1":  # valor
                valor = campo_2
                if base_calculo > 0:
                    margem = ((valor - base_calculo) / base_calculo) * Decimal('100.00')
                else:
                    margem = Decimal('0.00')
            else:
                return JsonResponse({'ok': False, 'msg': 'Tipo de atribuição inválido.'})
            ProdutoTabela.objects.update_or_create(
                produto=produto,
                tabela=tabela,
                defaults={
                    'vl_prod': valor,
                    'margem': margem,
                }
            )
            valores_ret[str(pid)] = {
                'vl_prod': float(valor),
                'margem': float(margem),
            }
        return JsonResponse({
            'ok': True,
            'tabela_nome': getattr(tabela, 'descricao', str(tabela)),
            'valores': valores_ret,
        })
    except TabelaPreco.DoesNotExist:
        return JsonResponse({'ok': False, 'msg': 'Tabela de preço não encontrada.'})
    except Produto.DoesNotExist:
        return JsonResponse({'ok': False, 'msg': 'Um dos produtos não foi encontrado.'})
    except (InvalidOperation, ValueError, TypeError) as e:
        return JsonResponse({'ok': False, 'msg': f'Erro nos valores enviados: {e}'})
    except Exception as e:
        return JsonResponse({'ok': False, 'msg': str(e)})

@login_required
def lista_produtos_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        filtros = Q(situacao__iexact='Ativo')
        if termo_busca.isdigit():
            condicao_busca = Q(desc_prod__icontains=termo_busca) | Q(id=termo_busca) | Q(desc_normalizado__icontains=termo_busca) | Q(codigos__codigo__icontains=termo_busca)
        else:
            condicao_busca = Q(desc_prod__icontains=termo_busca) | Q(desc_normalizado__icontains=termo_busca)
        produtos = Produto.objects.filter(filtros & condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': produto.id, 'text': f"{produto.id} - {produto.desc_prod.upper()}", 'desc_prod': produto.desc_prod} for produto in produtos]
        return JsonResponse({'results': results})
    except Exception as e:
        print(f"Erro na busca AJAX: {e}")
        return JsonResponse({'results': [], 'error': str(e)})

@login_required
def buscar_produtos(request):
    termo = request.GET.get('s', '').strip()
    filtro = request.GET.get('tp', 'desc')  # desc | cod
    tp_produto = request.GET.get('tp_prod', '')  # Principal | Adicional | ''
    tabela_id = request.GET.get('tabela_id')
    auto = request.GET.get('auto') == '1'
    produtos = Produto.objects.none()
    empresa = request.user.empresa
    if filtro == 'desc':
        norm_termo = remove_accents(termo).lower()
        produtos = Produto.objects.filter(vinc_emp=empresa, lista_orc=True).filter(Q(desc_prod__icontains=termo) | Q(desc_normalizado__icontains=norm_termo))
        if tp_produto: produtos = produtos.filter(tp_prod__icontains=tp_produto)
    elif filtro == 'cod' and termo:
        produtos = Produto.objects.filter(vinc_emp=empresa, situacao="Ativo").filter(Q(id=int(termo)) if termo.isdigit() else Q(pk__isnull=False))
        if termo.isdigit():
            produtos = Produto.objects.filter(vinc_emp=empresa, situacao="Ativo").filter(Q(id=int(termo)) | Q(codigos__codigo__iexact=termo)).distinct()
        else:
            produtos = Produto.objects.filter(vinc_emp=empresa, situacao="Ativo",codigos__codigo__iexact=termo).distinct()
        if tp_produto:
            produtos = produtos.filter(tp_prod__icontains=tp_produto)
    produtos = (produtos.select_related('unidProd', 'grupo').order_by('id'))
    data = []
    for prod in produtos:
        tabela = None
        if tabela_id:
            tabela = ProdutoTabela.objects.filter(produto=prod, tabela_id=tabela_id, tabela__vinc_emp=empresa).first()
        data.append({'id': prod.id, 'desc_prod': prod.desc_prod, 'unidProd': prod.unidProd.nome_unidade if prod.unidProd else '', 'grupo': prod.grupo.nome_grupo if prod.grupo else '', 'estoque_prod': getattr(prod, 'estoque_prod', None), 'vl_compra': prod.vl_compra, 'vl_prod': float(tabela.vl_prod) if tabela else None, 'tp_prod': prod.tp_prod, 'especifico': prod.especifico if prod.especifico else ''})
    return JsonResponse({'produtos': data})

@login_required
def buscar_produtos_ent(request):
    empresa = request.user.empresa
    termo = request.GET.get('s', '').strip()
    filtro = request.GET.get('tp', 'desc')
    tp_produto = request.GET.get('tp_prod', '')
    gp_produto = request.GET.get('gp_prod', '')
    marc_produto = request.GET.get('marc_prod', '')
    unid_produto = request.GET.get('unid_prod', '')
    num_pagina = request.GET.get('num_pag', '10')
    page = request.GET.get('page', 1)

    if filtro == 'desc':
        norm_termo = remove_accents(termo).lower()
        produtos = Produto.objects.filter(vinc_emp=empresa, situacao="Ativo").filter(Q(desc_prod__icontains=termo) | Q(desc_normalizado__icontains=norm_termo))
        if tp_produto: produtos = produtos.filter(tp_prod=tp_produto)
        if marc_produto: produtos = produtos.filter(marca=marc_produto)
        if gp_produto: produtos = produtos.filter(grupo=gp_produto)
        if unid_produto: produtos = produtos.filter(unidProd=unid_produto)
        produtos = produtos.order_by('id')
    elif filtro == 'cod':
        if termo:
            produtos = Produto.objects.filter(vinc_emp=empresa, situacao="Ativo").filter(Q(id=int(termo)) if termo.isdigit() else Q(pk__isnull=False))
            if termo.isdigit():
                produtos = Produto.objects.filter(vinc_emp=empresa, situacao="Ativo").filter(Q(id=int(termo)) | Q(codigos__codigo__iexact=termo)).distinct()
            else:
                produtos = Produto.objects.filter(vinc_emp=empresa, situacao="Ativo",codigos__codigo__iexact=termo).distinct()
            if tp_produto: produtos = produtos.filter(tp_prod=tp_produto)
            if marc_produto: produtos = produtos.filter(marca=marc_produto)
            if gp_produto: produtos = produtos.filter(grupo=gp_produto)
            if unid_produto: produtos = produtos.filter(unidProd=unid_produto)
            produtos = produtos.order_by('id')
        else:
            produtos = Produto.objects.none()
    else: produtos = Produto.objects.none()
    if num_pagina == 'todos': qtd_pag = produtos.count() or 1
    else:
        try: qtd_pag = int(num_pagina) if int(num_pagina) > 0 else 1
        except ValueError: qtd_pag = 10
    paginator = Paginator(produtos, qtd_pag)
    produtos_page = paginator.get_page(page)
    data = []
    for prod in produtos_page.object_list:
        tabela = ProdutoTabela.objects.filter(produto=prod, tabela__vinc_emp=empresa).first()
        vl_compra = float(prod.vl_compra or 0)
        vl_prod = 0
        if tabela and tabela.vl_prod is not None: vl_prod = float(tabela.vl_prod)
        data.append({
            'id': prod.id, 'desc_prod': prod.desc_prod, 'unidProd': prod.unidProd.nome_unidade if prod.unidProd else '', 'marca': prod.marca.nome_marca if prod.marca else '', 'grupo': prod.grupo.nome_grupo if prod.grupo else '',
            'estoque_prod': getattr(prod, 'estoque_prod', None), 'vl_compra': vl_compra, 'vl_prod': vl_prod, 'tp_prod': prod.tp_prod,
        })
    return JsonResponse({'produtos': data, 'page': produtos_page.number, 'num_pages': paginator.num_pages, 'has_next': produtos_page.has_next(), 'has_prev': produtos_page.has_previous()})

@login_required
def buscar_tabelas_produto_ajax(request):
    produto_id = request.GET.get('produto_id')
    if not produto_id:
        return JsonResponse({'ok': False, 'msg': 'Produto não informado.'}, status=400)

    try:
        produto = Produto.objects.get(pk=produto_id, vinc_emp=request.user.empresa)

        tabelas = ProdutoTabela.objects.filter(
            produto=produto,
            tabela__vinc_emp=request.user.empresa
        ).select_related('tabela').order_by('tabela__descricao')

        data = []
        for item in tabelas:
            data.append({
                'tabela_id': item.tabela_id,
                'tabela_nome': item.tabela.descricao,
                'margem': f"{item.margem:.2f}",
                'valor': f"{item.vl_prod:.2f}",
            })

        return JsonResponse({'ok': True, 'tabelas': data})

    except Produto.DoesNotExist:
        return JsonResponse({'ok': False, 'msg': 'Produto não encontrado.'}, status=404)

@login_required
@require_POST
@transaction.atomic
def salvar_tabelas_produto_ajax(request):
    if not request.user.has_perm('produtos.change_produto'):
        return JsonResponse({'ok': False, 'msg': 'Você não tem permissão para alterar produtos.'}, status=403)
    try:
        body = json.loads(request.body or '{}')
        produto_id = body.get('produto_id')
        tabelas = body.get('tabelas', [])
        if not produto_id:
            return JsonResponse({'ok': False, 'msg': 'Produto não informado.'}, status=400)
        produto = Produto.objects.get(pk=produto_id, vinc_emp=request.user.empresa)
        tabelas_ids_recebidas = []
        for tab in tabelas:
            tabela_id = tab.get('tabela_id')
            if not tabela_id:
                continue
            tabela = TabelaPreco.objects.filter(
                pk=tabela_id,
                vinc_emp=request.user.empresa
            ).first()
            if not tabela:
                continue
            try:
                vl_prod = str_para_decimal(str(tab.get('valor', '0')))
            except Exception:
                vl_prod = Decimal('0.00')
            try:
                margem = str_para_decimal(str(tab.get('margem', '0')))
            except Exception:
                margem = Decimal('0.00')
            ProdutoTabela.objects.update_or_create(
                produto=produto,
                tabela=tabela,
                defaults={
                    'vl_prod': vl_prod,
                    'margem': margem
                }
            )
            tabelas_ids_recebidas.append(tabela.id)
        ProdutoTabela.objects.filter(
            produto=produto
        ).exclude(
            tabela_id__in=tabelas_ids_recebidas
        ).delete()
        return JsonResponse({'ok': True, 'msg': 'Tabelas do produto salvas com sucesso.'})
    except Produto.DoesNotExist:
        return JsonResponse({'ok': False, 'msg': 'Produto não encontrado.'}, status=404)
    except Exception as e:
        return JsonResponse({'ok': False, 'msg': str(e)}, status=500)

def str_para_decimal(valor_str):
    if not valor_str:
        return Decimal('0.00')
    valor_limpo = re.sub(r'[^\d,.-]', '', valor_str)
    valor_limpo = valor_limpo.replace(',', '.')
    try:
        return Decimal(valor_limpo)
    except InvalidOperation:
        return Decimal('0.00')

@login_required
@transaction.atomic
def add_produto(request):
    error_messages = []
    empresa = request.user.empresa
    form = ProdutoForm(empresa=empresa)
    if not request.user.has_perm('produtos.add_produto'):
        messages.info(request, 'Você não tem permissão para adicionar produtos.')
        return redirect('/produtos/lista/')
    try:
        if request.method == "POST":
            form = ProdutoForm(request.POST, empresa=empresa)
            lista_orc = request.POST.get('lista_orc') == 'on'
            if not form.is_valid():
                error_messages = [
                    f"Campo ({field.label}) é obrigatório!"
                    for field in form if field.errors
                ]
                return render(request, 'produtos/add_produto.html', {'form': form, 'error_messages': error_messages})
            p = form.save(commit=False)
            # Validação extra de segurança para multiempresa
            if p.unidProd and p.unidProd.vinc_emp != empresa:
                return HttpResponseForbidden()
            if p.grupo and p.grupo.vinc_emp != empresa:
                return HttpResponseForbidden()
            if p.marca and p.marca.vinc_emp != empresa:
                return HttpResponseForbidden()
            p.vinc_emp = empresa
            p.lista_orc = lista_orc
            p.save()
            tab_preco_dict = {}
            for key, value in request.POST.items():
                if key.startswith("tab_preco["):
                    m = re.match(r"tab_preco\[(\d+)\]\[(\w+)\]", key)
                    if m:
                        idx, campo = m.groups()
                        if idx not in tab_preco_dict:
                            tab_preco_dict[idx] = {}
                        tab_preco_dict[idx][campo] = value
            for dados in tab_preco_dict.values():
                tabela_id = dados.get("tabela")
                margem = dados.get("margem")
                vl_prod = dados.get("vl_prod")
                if not tabela_id or not vl_prod:
                    continue
                try:
                    tabela = TabelaPreco.objects.get(pk=tabela_id, vinc_emp=empresa)
                except TabelaPreco.DoesNotExist:
                    messages.warning(request, f"Tabela {tabela_id} não encontrada.")
                    continue
                try:
                    vl_prod_decimal = str_para_decimal(vl_prod)
                except Exception:
                    vl_prod_decimal = Decimal('0.00')
                try:
                    margem_decimal = str_para_decimal(margem)
                except Exception:
                    margem_decimal = Decimal('0.00')
                ProdutoTabela.objects.create(produto=p, tabela=tabela, vl_prod=vl_prod_decimal, margem=margem_decimal)
            cod_sec_dict = {}
            for key, value in request.POST.items():
                if key.startswith("codigo["):
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
                # Validação por empresa
                if CodigoProduto.objects.filter(codigo=codigo, produto__vinc_emp=empresa).exists():
                    messages.warning(request, f"O código '{codigo}' já está vinculado a outro produto desta empresa.")
                    continue
                CodigoProduto.objects.create(produto=p, codigo=codigo, vinc_emp=empresa)
            messages.success(request, 'Produto adicionado com sucesso!')
            return redirect(f'/produtos/lista/?tp=cod&s={p.id}')
    except ObjectDoesNotExist:
        error_messages.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {str(e)}")
    except DatabaseError as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco de dados: {str(e)}")
    except Exception as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return render(request, 'produtos/add_produto.html', {'form': form, 'error_messages': error_messages})

@login_required
@transaction.atomic
def att_produto(request, id):
    error_messages = []
    empresa = request.user.empresa
    form = None
    p = None
    todas_tabelas = TabelaPreco.objects.none()
    prod_tabelas = ProdutoTabela.objects.none()
    if not request.user.has_perm('produtos.change_produto'):
        messages.info(request, 'Você não tem permissão para editar produtos.')
        return redirect('/produtos/lista/')
    try:
        p = get_object_or_404(Produto, pk=id, vinc_emp=empresa)
        if request.method == "POST":
            form = ProdutoForm(request.POST, instance=p, empresa=empresa)
            lista_orc = request.POST.get('lista_orc') == 'on'
            if not form.is_valid():
                error_messages = [
                    f"Campo ({field.label}) é obrigatório!"
                    for field in form if field.errors
                ]
                todas_tabelas = TabelaPreco.objects.filter(vinc_emp=empresa)
                prod_tabelas = p.produtotabela_set.select_related('tabela').filter(tabela__vinc_emp=empresa)
                return render(request, 'produtos/att_produto.html', {'form': form, 'p': p, 'tabelas': todas_tabelas, 'prod_tabelas': prod_tabelas, 'codigos': p.codigos.all(), 'error_messages': error_messages})
            estoque_atual = p.estoque_prod
            p = form.save(commit=False)
            # Garante que continue na empresa do usuário
            p.vinc_emp = empresa
            # Mantém estoque anterior se vier vazio
            if p.estoque_prod in [None, '']:
                p.estoque_prod = estoque_atual
            p.lista_orc = lista_orc
            p.save()
            tab_preco_dict = {}
            for key, value in request.POST.items():
                if key.startswith("tab_preco["):
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
                    tabela = TabelaPreco.objects.get(pk=tabela_id, vinc_emp=empresa)
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
            # Remove tabelas antigas não reenviadas, somente da empresa atual
            ProdutoTabela.objects.filter(
                produto=p,
                tabela__vinc_emp=empresa
            ).exclude(id__in=tab_preco_ids).delete()
            cod_sec_dict = {}
            for key, value in request.POST.items():
                if key.startswith("codigo["):
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
                # Verifica se já existe em outro produto da MESMA empresa
                if CodigoProduto.objects.filter(codigo=codigo, produto__vinc_emp=empresa).exclude(produto=p).exists():
                    messages.warning(request, f"O código '{codigo}' já está vinculado a outro produto desta empresa.")
                    continue
                ep, created = CodigoProduto.objects.get_or_create(produto=p, codigo=codigo, vinc_emp=empresa)
                cod_sec_ids.append(ep.id)
            # Remove códigos antigos não reenviados
            CodigoProduto.objects.filter(produto=p).exclude(id__in=cod_sec_ids).delete()
            messages.success(request, 'Produto atualizado com sucesso!')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            else:
                return redirect(f'/produtos/lista/?tp=cod&s={p.id}')
        else:
            form = ProdutoForm(instance=p, empresa=empresa)
        todas_tabelas = TabelaPreco.objects.filter(vinc_emp=empresa)
        prod_tabelas = p.produtotabela_set.select_related('tabela').filter(tabela__vinc_emp=empresa)
    except ObjectDoesNotExist:
        error_messages.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {str(e)}")
    except DatabaseError as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except Exception as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return render(request, 'produtos/att_produto.html', {'form': form, 'p': p, 'tabelas': todas_tabelas, 'prod_tabelas': prod_tabelas, 'codigos': p.codigos.all() if p else [], 'error_messages': error_messages})

@login_required
@transaction.atomic
def clonar_produto(request, id):
    error_messages = []
    empresa = request.user.empresa
    form = None
    p = None
    todas_tabelas = TabelaPreco.objects.none()
    prod_tabelas = ProdutoTabela.objects.none()
    if not request.user.has_perm('produtos.clonar_produto'):
        messages.info(request, 'Você não tem permissão para clonar produtos.')
        return redirect('/produtos/lista/')
    try:
        p = get_object_or_404(Produto, pk=id, vinc_emp=empresa)
        if request.method == 'POST':
            post_data = request.POST.copy()
            if not post_data.get('estoque_prod', '').strip():
                post_data['estoque_prod'] = '0.00'
            form = ProdutoForm(post_data, empresa=empresa)
            lista_orc = post_data.get('lista_orc') == 'on'
            if form.is_valid():
                novo_produto = form.save(commit=False)

                if novo_produto.unidProd and novo_produto.unidProd.vinc_emp != empresa:
                    return HttpResponseForbidden()
                if novo_produto.grupo and novo_produto.grupo.vinc_emp != empresa:
                    return HttpResponseForbidden()
                if novo_produto.marca and novo_produto.marca.vinc_emp != empresa:
                    return HttpResponseForbidden()
                novo_produto.vinc_emp = empresa
                novo_produto.lista_orc = lista_orc
                novo_produto.estoque_prod = Decimal('0.00')
                novo_produto.save()
                tab_preco_dict = {}
                for key, value in request.POST.items():
                    if key.startswith("tab_preco["):
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
                        tabela = TabelaPreco.objects.get(pk=tabela_id, vinc_emp=empresa)
                    except TabelaPreco.DoesNotExist:
                        messages.warning(request, f"Tabela {tabela_id} não encontrada.")
                        continue
                    vl_prod_decimal = str_para_decimal(vl_prod)
                    margem_decimal = str_para_decimal(margem)
                    ep = ProdutoTabela.objects.create(produto=novo_produto, tabela=tabela, vl_prod=vl_prod_decimal, margem=margem_decimal)
                    tab_preco_ids.append(ep.id)
                # Se nenhuma tabela foi enviada via POST, clona as existentes do produto original
                if not tab_preco_ids:
                    for tabela_antiga in p.produtotabela_set.select_related('tabela').filter(tabela__vinc_emp=empresa):
                        ProdutoTabela.objects.create(produto=novo_produto, tabela=tabela_antiga.tabela, vl_prod=tabela_antiga.vl_prod, margem=tabela_antiga.margem)
                cod_sec_dict = {}
                for key, value in request.POST.items():
                    if key.startswith("codigo["):
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
                    # Verifica se já existe esse código em outro produto da mesma empresa
                    if CodigoProduto.objects.filter(codigo=codigo, produto__vinc_emp=empresa).exists():
                        messages.warning(request, f"O código '{codigo}' já está vinculado a outro produto desta empresa.")
                        continue
                    # Cria o código somente se ele foi informado manualmente no clone
                    CodigoProduto.objects.create(produto=novo_produto, codigo=codigo, vinc_emp=empresa)
                messages.success(request, 'Produto clonado com sucesso!')
                return redirect(f'/produtos/lista/?tp=cod&s={novo_produto.id}')
            else:
                for field in form:
                    if field.errors:
                        for error in field.errors:
                            error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
                todas_tabelas = TabelaPreco.objects.filter(vinc_emp=empresa)
                prod_tabelas = p.produtotabela_set.select_related('tabela').filter(tabela__vinc_emp=empresa)
                return render(request, 'produtos/clonar.html', {'form': form, 'p': p, 'tabelas': todas_tabelas, 'prod_tabelas': prod_tabelas, 'codigos': p.codigos.all(), 'error_messages': error_messages})
        else:
            form = ProdutoForm(instance=p, empresa=empresa)
            form.fields['estoque_prod'].initial = 0.00
        todas_tabelas = TabelaPreco.objects.filter(vinc_emp=empresa)
        prod_tabelas = p.produtotabela_set.select_related('tabela').filter(tabela__vinc_emp=empresa)
    except ObjectDoesNotExist:
        error_messages.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {str(e)}")
    except DatabaseError as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except Exception as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return render(request, 'produtos/clonar.html', {'form': form, 'p': p, 'tabelas': todas_tabelas, 'prod_tabelas': prod_tabelas, 'codigos': p.codigos.all() if p else [], 'error_messages': error_messages})

@login_required
def del_produto(request, id):
    if not request.user.has_perm('produtos.delete_produto'):
        messages.info(request, 'Você não tem permissão para deletar produtos.')
        return redirect('lista-produtos')
    if request.method == "POST":
        p = get_object_or_404(Produto, pk=id, vinc_emp=request.user.empresa)
        p.delete()
        transaction.commit()
        connection.close()
        messages.success(request, 'Produto deletado com sucesso!')
    return redirect(reverse('lista-produtos'))