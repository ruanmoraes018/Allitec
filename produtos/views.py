from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Produto, ProdutoTabela, CodigoProduto, SaldoEstoque, MovimentoEstoque
from .forms import ProdutoForm
import unicodedata
from django.http import JsonResponse, HttpResponseForbidden
from filiais.models import Usuario, Filial
from util.permissoes import verifica_permissao
from grupos.models import Grupo
from marcas.models import Marca
from unidades.models import Unidade
from tabelas_preco.models import TabelaPreco
from decimal import Decimal, InvalidOperation
import re
from django.urls import reverse
from django.db.models import Q
from django.db import DatabaseError, IntegrityError, transaction
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.http import require_POST
import json
from util.parse_decimal import parse_decimal
from util.logs import gerar_alteracoes, registrar_log
from .services import criar_alerta, resolver_alerta, adicionar_estoque, ajustar_estoque
from estoques.models import Estoque

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
    filial_user = request.user.filial_user
    estoque_padrao = None
    if filial_user:
        filial_estoque = getattr(filial_user, 'estoque', None)
        if filial_estoque:
            estoque_padrao = filial_estoque.estoque_padrao
    produtos_qs = Produto.objects.filter(vinc_emp=empresa)
    if ordem == '0': produtos_qs = produtos_qs.order_by('desc_prod')
    elif ordem == '1': produtos_qs = produtos_qs.order_by('codigo')
    else: produtos_qs = produtos_qs.order_by(ordem)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        produtos_qs = produtos_qs.filter(desc_prod__icontains=norm_s)
    elif tp == 'cod':
        if s:
            try: produtos_qs = produtos_qs.filter(codigo__iexact=s)
            except ValueError:  produtos_qs = Produto.objects.none()
    if tp_produto in ['Principal', 'Adicional']: produtos_qs = produtos_qs.filter(tp_prod__exact=tp_produto)
    if sit == '1': produtos_qs = produtos_qs.filter(situacao='Ativo')
    elif sit == '2': produtos_qs = produtos_qs.filter(situacao='Inativo')
    if grupo: produtos_qs = produtos_qs.filter(grupo__codigo=grupo)
    if marca: produtos_qs = produtos_qs.filter(marca__codigo=marca)
    if unid: produtos_qs = produtos_qs.filter(unidProd__codigo=unid)
    if reg == 'todos': num_pagina = produtos_qs.count() or 1
    else:
        try: num_pagina = int(reg) if int(reg) > 0 else 10
        except ValueError: num_pagina = 10
    paginator = Paginator(produtos_qs, num_pagina)
    page = request.GET.get('page')
    produtos_qs = paginator.get_page(page)
    produtos_ids = [p.codigo for p in produtos_qs]
    saldos_map = {}
    estoque_padrao_map = {}
    saldos = (SaldoEstoque.objects.filter(produto__codigo__in=produtos_ids,produto__vinc_emp=empresa,estoque__empresa=empresa,).select_related('estoque','estoque__filial',))
    for saldo in saldos:
        filial = saldo.estoque.filial
        # Todos os saldos do produto
        saldos_map.setdefault(saldo.produto.codigo,[]).append({'filial_codigo': filial.codigo,'filial_nome': filial.fantasia,'estoque_codigo': saldo.estoque.codigo,
            'estoque_nome': saldo.estoque.descricao,'quantidade': float(saldo.quantidade or 0),
        })
        # Saldo do estoque padrão da filial do usuário
        if estoque_padrao and saldo.estoque_id == estoque_padrao.id:
            estoque_padrao_map[saldo.produto.codigo] = float(saldo.quantidade or 0)
    tabelas_map = {}
    if produtos_ids:
        tabelas = (ProdutoTabela.objects.filter(produto__codigo__in=produtos_ids, produto__vinc_emp=empresa).select_related('tabela'))
        for tab in tabelas:
            tabelas_map.setdefault(tab.produto.codigo,[]).append({"id":tab.tabela.codigo,"descricao":tab.tabela.descricao if tab.tabela else str(tab),"vl_prod": float(tab.vl_prod)})
    for p in produtos_qs:
        p.tab_conv = tabelas_map.get(p.codigo, [])
        p.estoque_prod = estoque_padrao_map.get(p.codigo, 0)
    marcas = Marca.objects.filter(vinc_emp=empresa)
    grupos = Grupo.objects.filter(vinc_emp=empresa)
    unidades = Unidade.objects.filter(vinc_emp=empresa)
    return render(request,'produtos/lista.html',{'produtos':produtos_qs,'s': s,'tp':tp,'sit':sit,'ordem':ordem,'marca':marca,'marcas':marcas,'grupo':grupo,'grupos':grupos,
        'unidades':unidades, 'unid': unid, 'reg': reg, 'tp_produto': tp_produto
    })

@login_required
def saldos_estoque_produto(request, codigo):
    empresa = request.user.empresa
    produto = (Produto.objects.filter(codigo=codigo,vinc_emp=empresa,).first())
    if not produto:
        return JsonResponse({'erro': 'Produto não encontrado.'},status=404)
    saldos = (SaldoEstoque.objects.filter(produto=produto,estoque__empresa=empresa,).select_related('estoque','estoque__filial',).order_by('estoque__filial__codigo','estoque__codigo',))
    filiais = {}
    for saldo in saldos:
        filial = saldo.estoque.filial
        filiais.setdefault(filial.codigo,{'codigo': filial.codigo,'nome': filial.fantasia,'estoques': [],})
        filiais[filial.codigo]['estoques'].append({'codigo': saldo.estoque.codigo,'nome': saldo.estoque.descricao,'quantidade': float(saldo.quantidade or 0),})
    return JsonResponse({'produto': {'codigo': produto.codigo,'descricao': produto.desc_prod,},'filiais': list(filiais.values()),})

@login_required
@require_POST
def precos_tabela_lote(request):
    try:
        empresa = request.user.empresa
        data = json.loads(request.body)
        tabela_id = data.get('tabela_id')
        produtos = data.get('produtos', [])
        if not tabela_id or not produtos:
            return JsonResponse({"precos": {}})

        precos_qs = (ProdutoTabela.objects
            .filter(tabela__codigo=tabela_id,
                    tabela__vinc_emp=empresa,
                    produto__codigo__in=produtos,
                    produto__vinc_emp=empresa)
            .values('produto__codigo', 'vl_prod'))

        mapa = {str(p['produto__codigo']): float(p['vl_prod']) for p in precos_qs}
        return JsonResponse({"precos": mapa})
    except Exception as e:
        return JsonResponse({"erro": str(e), "precos": {}}, status=500)

@login_required
def att_prod_lote(request):
    try:
        with transaction.atomic():
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
                produtos = Produto.objects.filter(codigo__in=produtos_ids, vinc_emp=empresa)
                if not produtos.exists():
                    messages.info(request, 'Nenhum produto selecionado.')
                    return redirect('/produtos/lista/')
                alguma_alteracao = False
                gp = None
                unidade = None
                marca = None
                it_old = None
                if switch_grupo == 'on' and grupo_id: gp = Grupo.objects.filter(codigo=grupo_id, vinc_emp=empresa).first()
                if switch_unidade == 'on' and unidade_id: unidade = Unidade.objects.filter(codigo=unidade_id, vinc_emp=empresa).first()
                if switch_marca == 'on' and marca_id: marca = Marca.objects.filter(codigo=marca_id, vinc_emp=empresa).first()
                for produto in produtos:
                    if switch_grupo == 'on' and grupo_id and gp:
                        produto.grupo = gp
                        alguma_alteracao = True
                        it_old = Produto.objects.get(codigo=produto.codigo, vinc_emp=request.user.empresa)
                    if switch_unidade == 'on' and unidade_id and unidade:
                        produto.unidProd = unidade
                        alguma_alteracao = True
                        it_old = Produto.objects.get(codigo=produto.codigo, vinc_emp=request.user.empresa)
                    if switch_lista_orc == 'on':
                        produto.lista_orc = True
                        alguma_alteracao = True
                        it_old = Produto.objects.get(codigo=produto.codigo, vinc_emp=request.user.empresa)
                    if switch_marca == 'on' and marca_id and marca:
                        produto.marca = marca
                        alguma_alteracao = True
                        it_old = Produto.objects.get(codigo=produto.codigo, vinc_emp=request.user.empresa)
                    if switch_situacao == 'on' and situacao in ['Ativo', 'Inativo']:
                        produto.situacao = situacao
                        alguma_alteracao = True
                        it_old = Produto.objects.get(codigo=produto.codigo, vinc_emp=request.user.empresa)
                    produto.save()
                    registrar_log(request,"ALTERAR","Produto",produto.desc_prod,f"Alterou o produto: {produto.codigo}",produto.id,gerar_alteracoes(it_old,produto))
                if alguma_alteracao: messages.success(request, 'Campos atualizados com sucesso!')
                else: messages.info(request, 'Nenhuma alteração realizada.')
            else: messages.info(request, 'Nenhuma alteração realizada.')
            return redirect('/produtos/lista/')
    except ObjectDoesNotExist: messages.error("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        detalhe = str(e.__cause__ if e.__cause__ else e)
        messages.error(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {detalhe}")
    except DatabaseError as e: messages.error(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except ValueError as e: messages.error(f"<i class='fa-solid fa-xmark'></i> {str(e)}")
    except Exception as e: messages.error(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return redirect('/produtos/lista/')

@login_required
def att_preco_lote(request):
    try:
        with transaction.atomic():
            if request.method == "POST":
                produtos_ids = request.POST.getlist('prod-prec')
                tabela_id = request.POST.get('tb-prec')
                tp_atrib = request.POST.get('tp-atrib')  # 0 = Margem, 1 = Valor
                campo_1 = request.POST.get('campo_1', '').replace(',', '.').strip()
                produtos = Produto.objects.filter(codigo__in=produtos_ids, vinc_emp=request.user.empresa)
                if not produtos.exists():
                    messages.info(request, 'Nenhum produto selecionado.')
                    return redirect('/produtos/lista/')
                try: tabela = TabelaPreco.objects.get(codigo=tabela_id, vinc_emp=request.user.empresa)
                except TabelaPreco.DoesNotExist:
                    messages.error(request, 'Tabela de preço não encontrada.')
                    return redirect('/produtos/lista/')
                try: val_1 = Decimal(campo_1 or '0')
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
                    it_old = Produto.objects.get(codigo=p.codigo, vinc_emp=request.user.empresa)
                    registrar_log(request, "ALTERAR", "Produto", p.desc_prod, f"Alterou a tabela de preço do produto: {p.codigo} - {p.desc_prod}", p.id, gerar_alteracoes(it_old, p))
                if alguma_alteracao:
                    tipo_label = "margem" if tp_atrib == "0" else "valor"
                    messages.success(request, f"Tabela de preço atualizada com base em {tipo_label} com sucesso!")
                else: messages.info(request, 'Nenhuma alteração realizada.')
            return redirect('/produtos/lista/')
    except ObjectDoesNotExist: messages.error("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        detalhe = str(e.__cause__ if e.__cause__ else e)
        messages.error(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {detalhe}")
    except DatabaseError as e: messages.error(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except ValueError as e: messages.error(f"<i class='fa-solid fa-xmark'></i> {str(e)}")
    except Exception as e: messages.error(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return redirect('/produtos/lista/')

@login_required
@require_POST
def att_tb_preco_lote(request):
    empresa = request.user.empresa
    try:
        with transaction.atomic():
            body = json.loads(request.body or '{}')
            tabela_id = body.get('tabela_id')
            tipo = str(body.get('tipo', '')).strip()
            campo_1 = Decimal(str(body.get('campo_1') or 0))
            campo_2 = Decimal(str(body.get('campo_2') or 0))
            produtos_req = body.get('produtos', [])
            if not tabela_id: return JsonResponse({'ok': False, 'msg': 'Selecione uma tabela de preço.'})
            if not produtos_req: return JsonResponse({'ok': False, 'msg': 'Nenhum produto foi selecionado.'})
            tabela = TabelaPreco.objects.get(codigo=tabela_id, vinc_emp=empresa)
            valores_ret = {}
            for item in produtos_req:
                pid = item.get('id')
                base_calculo = Decimal(str(item.get('base_calculo') or 0))
                produto = Produto.objects.get(codigo=pid, vinc_emp=empresa)
                margem = Decimal('0.00')
                valor = Decimal('0.00')
                if tipo == "0":  # margem
                    margem = campo_1
                    valor = base_calculo * (Decimal('1.00') + (margem / Decimal('100.00')))
                elif tipo == "1":  # valor
                    valor = campo_2
                    if base_calculo > 0: margem = ((valor - base_calculo) / base_calculo) * Decimal('100.00')
                    else: margem = Decimal('0.00')
                else:
                    return JsonResponse({'ok': False, 'msg': 'Tipo de atribuição inválido.'})
                ProdutoTabela.objects.update_or_create(produto=produto, tabela=tabela, defaults={'vl_prod': valor, 'margem': margem,})
                valores_ret[str(pid)] = {'vl_prod': float(valor), 'margem': float(margem),}
                it_old = Produto.objects.get(codigo=item.codigo, vinc_emp=request.user.empresa)
                registrar_log(request,"ALTERAR","Produto",item.desc_prod,f"Alterou a tabela de preço do produto: {item.codigo}",item.id,gerar_alteracoes(it_old,item))
            return JsonResponse({'ok': True, 'tabela_nome': getattr(tabela, 'descricao', str(tabela)), 'valores': valores_ret,})
    except TabelaPreco.DoesNotExist: return JsonResponse({'ok': False, 'msg': 'Tabela de preço não encontrada.'})
    except Produto.DoesNotExist: return JsonResponse({'ok': False, 'msg': 'Um dos produtos não foi encontrado.'})
    except (InvalidOperation, ValueError, TypeError) as e: return JsonResponse({'ok': False, 'msg': f'Erro nos valores enviados: {e}'})
    except Exception as e: return JsonResponse({'ok': False, 'msg': str(e)})

@login_required
def lista_produtos_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        filtros = Q(situacao__iexact='Ativo')
        if termo_busca.isdigit():
            condicao_busca = Q(desc_prod__icontains=termo_busca) | Q(codigo=termo_busca) | Q(desc_normalizado__icontains=termo_busca) | Q(codigos__codigo__icontains=termo_busca)
        else: condicao_busca = Q(desc_prod__icontains=termo_busca) | Q(desc_normalizado__icontains=termo_busca)
        produtos = Produto.objects.filter(filtros & condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': produto.codigo, 'text': f"{produto.codigo} - {produto.desc_prod.upper()}", 'desc_prod': produto.desc_prod} for produto in produtos]
        return JsonResponse({'results': results})
    except Exception as e: return JsonResponse({'results': [], 'error': str(e)})

@login_required
def buscar_produtos(request):
    termo = request.GET.get('s', '').strip()
    filtro = request.GET.get('tp', 'desc')  # desc | cod
    tp_produto = request.GET.get('tp_prod', '')  # Principal | Adicional | ''
    tabela_id = request.GET.get('tabela_id')
    produtos = Produto.objects.none()
    empresa = request.user.empresa
    if filtro == 'desc':
        norm_termo = remove_accents(termo).lower()
        produtos = Produto.objects.filter(vinc_emp=empresa, lista_orc=True).filter(Q(desc_prod__icontains=termo) | Q(desc_normalizado__icontains=norm_termo))
        if tp_produto: produtos = produtos.filter(tp_prod__icontains=tp_produto)
    elif filtro == 'cod' and termo:
        produtos = Produto.objects.filter(vinc_emp=empresa, situacao="Ativo").filter(Q(codigo=int(termo)) if termo.isdigit() else Q(pk__isnull=False))
        if termo.isdigit(): produtos = Produto.objects.filter(vinc_emp=empresa, situacao="Ativo").filter(Q(codigo=int(termo)) | Q(codigos__codigo__iexact=termo)).distinct()
        else: produtos = Produto.objects.filter(vinc_emp=empresa, situacao="Ativo",codigos__codigo__iexact=termo).distinct()
        if tp_produto: produtos = produtos.filter(tp_prod__icontains=tp_produto)
    produtos = (produtos.select_related('unidProd', 'grupo').order_by('codigo'))
    data = []
    estoque_padrao = None
    if request.user.filial_user:
        estoque_padrao = (getattr(request.user.filial_user.estoque, 'estoque_padrao', None) if hasattr(request.user.filial_user, 'estoque') else None)
    for p in produtos:
        tabela = None
        if tabela_id: tabela = ProdutoTabela.objects.filter(produto=p, tabela__codigo=tabela_id, tabela__vinc_emp=empresa).first()
        saldo = None
        if estoque_padrao:
            saldo = (SaldoEstoque.objects.filter(estoque=estoque_padrao,produto=p,).values_list('quantidade', flat=True).first())
        data.append({'id':p.codigo,'desc_prod':p.desc_prod,'unidProd':p.unidProd.nome_unidade,'grupo':p.grupo.nome_grupo,'estoque_prod':float(saldo or 0),'vl_compra':p.vl_compra,
            'vl_prod':float(tabela.vl_prod) if tabela else None,'tp_prod':p.tp_prod,'especifico':p.especifico if p.especifico else '',
            'diametro_eixo':float(p.diametro_eixo) if p.diametro_eixo else None,'espessura_lam':float(p.espessura_lam) if p.espessura_lam else None,
            'peso_m2':float(p.peso_m2) if p.peso_m2 else None, 'larg_port':float(p.larg_port) if p.larg_port else None, 'alt_port':float(p.alt_port) if p.alt_port else None
        })
    return JsonResponse({'produtos': data})

@login_required
def buscar_produtos_ent(request):
    empresa = request.user.empresa
    tabela_id = request.GET.get('tabela_id', '').strip()
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
        produtos = produtos.order_by('codigo')
    elif filtro == 'cod':
        if termo:
            produtos = Produto.objects.filter(vinc_emp=empresa, situacao="Ativo").filter(Q(codigo=int(termo)) if termo.isdigit() else Q(pk__isnull=False))
            if termo.isdigit(): produtos = Produto.objects.filter(vinc_emp=empresa, situacao="Ativo").filter(Q(codigo=int(termo)) | Q(codigos__codigo__iexact=termo)).distinct()
            else: produtos = Produto.objects.filter(vinc_emp=empresa, situacao="Ativo",codigos__codigo__iexact=termo).distinct()
            if tp_produto: produtos = produtos.filter(tp_prod=tp_produto)
            if marc_produto: produtos = produtos.filter(marca=marc_produto)
            if gp_produto: produtos = produtos.filter(grupo=gp_produto)
            if unid_produto: produtos = produtos.filter(unidProd=unid_produto)
            produtos = produtos.order_by('codigo')
        else: produtos = Produto.objects.none()
    else: produtos = Produto.objects.none()
    if num_pagina == 'todos': qtd_pag = produtos.count() or 1
    else:
        try: qtd_pag = int(num_pagina) if int(num_pagina) > 0 else 1
        except ValueError: qtd_pag = 10
    paginator = Paginator(produtos, qtd_pag)
    produtos_page = paginator.get_page(page)
    data = []
    estoque_padrao = None
    if request.user.filial_user:
        estoque_padrao = (getattr(request.user.filial_user.estoque, 'estoque_padrao', None) if hasattr(request.user.filial_user, 'estoque') else None)
    for prod in produtos_page.object_list:
        tabela = None
        if tabela_id:
            tabela = ProdutoTabela.objects.filter(produto=prod,tabela__codigo=tabela_id,tabela__vinc_emp=empresa).first()
        else:
            tabela = ProdutoTabela.objects.filter(produto=prod,tabela__vinc_emp=empresa).first()
        vl_compra = float(prod.vl_compra or 0)
        vl_prod = 0
        if tabela and tabela.vl_prod is not None: vl_prod = float(tabela.vl_prod)
        saldo = None
        if estoque_padrao:
            saldo = (SaldoEstoque.objects.filter(estoque=estoque_padrao,produto=prod,).values_list('quantidade', flat=True).first())
        data.append({
            'id':prod.codigo,'desc_prod':prod.desc_prod,'unidProd':prod.unidProd.nome_unidade if prod.unidProd else '','marca': prod.marca.nome_marca if prod.marca else '',
            'grupo':prod.grupo.nome_grupo if prod.grupo else '','estoque_prod': float(saldo or 0),'vl_compra':vl_compra,'vl_prod':vl_prod,'tp_prod':prod.tp_prod,
        })
    return JsonResponse({'produtos':data,'page':produtos_page.number,'num_pages':paginator.num_pages,'has_next':produtos_page.has_next(),'has_prev':produtos_page.has_previous()})

@login_required
def buscar_tabelas_produto_ajax(request):
    produto_id = request.GET.get('produto_id')
    if not produto_id: return JsonResponse({'ok': False, 'msg': 'Produto não informado.'}, status=400)
    try:
        produto = Produto.objects.get(codigo=produto_id, vinc_emp=request.user.empresa)
        tabelas = ProdutoTabela.objects.filter(produto=produto, tabela__vinc_emp=request.user.empresa).select_related('tabela').order_by('tabela__descricao')
        data = []
        for item in tabelas:
            data.append({'tabela_id': item.tabela.codigo, 'tabela_nome': item.tabela.descricao, 'margem': f"{item.margem:.2f}", 'valor': f"{item.vl_prod:.2f}",})
        return JsonResponse({'ok': True, 'tabelas': data})
    except Produto.DoesNotExist: return JsonResponse({'ok': False, 'msg': 'Produto não encontrado.'}, status=404)

@login_required
@require_POST
@transaction.atomic
def salvar_tabelas_produto_ajax(request):
    if not request.user.has_perm('produtos.change_produto'): return JsonResponse({'ok': False, 'msg': 'Você não tem permissão para alterar produtos.'}, status=403)
    try:
        with transaction.atomic():
            body = json.loads(request.body or '{}')
            produto_id = body.get('produto_id')
            tabelas = body.get('tabelas', [])
            if not produto_id: return JsonResponse({'ok': False, 'msg': 'Produto não informado.'}, status=400)
            produto = Produto.objects.get(codigo=produto_id, vinc_emp=request.user.empresa)
            tabelas_ids_recebidas = []
            for tab in tabelas:
                tabela_id = tab.get('tabela_id')
                if not tabela_id: continue
                tabela = TabelaPreco.objects.filter(codigo=tabela_id, vinc_emp=request.user.empresa).first()
                if not tabela: continue
                try: vl_prod = parse_decimal(str(tab.get('valor', '0')))
                except Exception: vl_prod = Decimal('0.00')
                try: margem = parse_decimal(str(tab.get('margem', '0')))
                except Exception: margem = Decimal('0.00')
                ProdutoTabela.objects.update_or_create(produto=produto, tabela=tabela, defaults={'vl_prod': vl_prod, 'margem': margem})
                tabelas_ids_recebidas.append(tabela.codigo)
                it_old = Produto.objects.get(codigo=produto.codigo, vinc_emp=request.user.empresa)
                registrar_log(request,"ALTERAR","Produto",produto.desc_prod,f"Alterou a tabela de preço do produto: {produto.codigo}",produto.id,gerar_alteracoes(it_old,produto))
            ProdutoTabela.objects.filter(produto=produto).exclude(tabela__codigo__in=tabelas_ids_recebidas).delete()
            return JsonResponse({'ok': True, 'msg': 'Tabelas do produto salvas com sucesso.'})
    except Produto.DoesNotExist: return JsonResponse({'ok': False, 'msg': 'Produto não encontrado.'}, status=404)
    except Exception as e: return JsonResponse({'ok': False, 'msg': str(e)}, status=500)

@login_required
def add_produto(request):
    error_messages = []
    empresa = request.user.empresa
    filiais = Filial.objects.filter(vinc_emp=empresa)
    if not request.user.has_perm('produtos.add_produto'):
        messages.info(request, 'Você não tem permissão para adicionar produtos.')
        return redirect('/produtos/lista/')
    if request.method != 'POST':
        form = ProdutoForm(empresa=empresa)
        return render(request, 'produtos/add_produto.html', {'form': form, 'error_messages': error_messages, 'filiais': filiais})
    form = ProdutoForm(request.POST, empresa=empresa)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'produtos/add_produto.html', {'form': form, 'error_messages': error_messages, 'filiais': filiais})
    try:
        with transaction.atomic():
            # PRODUTO
            lista_orc = request.POST.get('lista_orc') == 'on'
            p = form.save(commit=False)
            # Validação extra de segurança para multiempresa
            if p.unidProd and p.unidProd.vinc_emp != empresa: return HttpResponseForbidden()
            if p.grupo and p.grupo.vinc_emp != empresa: return HttpResponseForbidden()
            if p.marca and p.marca.vinc_emp != empresa: return HttpResponseForbidden()
            p.vinc_emp = empresa
            p.lista_orc = lista_orc
            # Os campos antigos continuam no model por enquanto, mas não serão mais utilizados para controlar o estoque.
            p.estoque_prod = Decimal('0.00')
            p.estoque_minimo = Decimal('0.00')
            p.estoque_maximo = Decimal('0.00')
            p.save()
            # ESTOQUES
            estoque_dict = {}
            for key, value in request.POST.items():
                if key.startswith("estoque["):
                    m = re.match(r"estoque\[(\d+)\]\[(\w+)\]", key)
                    if m:
                        idx, campo = m.groups()
                        if idx not in estoque_dict:
                            estoque_dict[idx] = {}
                        estoque_dict[idx][campo] = value
            for dados in estoque_dict.values():
                estoque_id = dados.get("estoque")
                if not estoque_id:
                    continue
                try: estoque = Estoque.objects.get(codigo=estoque_id, empresa=empresa)
                except Estoque.DoesNotExist:
                    messages.warning(request, f"Estoque {estoque_id} não encontrado.")
                    continue
                # Quantidade inicial
                try: quantidade = parse_decimal(dados.get("quantidade")) or Decimal('0.000')
                except Exception: quantidade = Decimal('0.000')
                # Estoque mínimo
                try: estoque_minimo = parse_decimal(dados.get("estoque_minimo")) or Decimal('0.000')
                except Exception: estoque_minimo = Decimal('0.000')
                # Estoque máximo
                try: estoque_maximo = parse_decimal(dados.get("estoque_maximo")) or Decimal('0.000')
                except Exception: estoque_maximo = Decimal('0.000')
                # Validações
                if quantidade < 0: raise ValueError(f'A quantidade do estoque "{estoque.descricao}" não pode ser negativa.')
                if estoque_minimo < 0: raise ValueError(f'O estoque mínimo do estoque "{estoque.descricao}" não pode ser negativo.')
                if estoque_maximo < 0: raise ValueError(f'O estoque máximo do estoque "{estoque.descricao}" não pode ser negativo.')
                if (estoque_maximo > 0 and estoque_minimo > estoque_maximo):
                    raise ValueError(f'O estoque mínimo do estoque "{estoque.descricao}" não pode ser maior que o estoque máximo.')
                # Cria o SaldoEstoque
                saldo = SaldoEstoque.objects.create(estoque=estoque, produto=p, quantidade=Decimal('0.000'), estoque_minimo=estoque_minimo, estoque_maximo=estoque_maximo)
                # Estoque inicial
                # Registra também o MovimentoEstoque
                if quantidade > 0:
                    adicionar_estoque(estoque=estoque, produto=p, quantidade=quantidade, usuario=request.user, descricao=(f'Cadastro do produto {p.codigo} - estoque inicial'))
                    saldo.refresh_from_db()
                # ALERTA DE ESTOQUE MÍNIMO
                if (saldo.estoque_minimo > 0 and saldo.quantidade <= saldo.estoque_minimo):
                    quantidade_alerta = (int(saldo.quantidade) if saldo.quantidade == int(saldo.quantidade) else saldo.quantidade)
                    criar_alerta(empresa=p.vinc_emp, tipo='ESTOQUE_MINIMO', referencia=p.codigo, titulo='Alerta de Estoque mínimo',
                        descricao=(f'Atenção! O produto ({p.desc_prod}) atingiu o estoque mínimo configurado e possui apenas {quantidade_alerta} unidades disponíveis no estoque '
                            f'{estoque.descricao}. Recomendamos realizar a reposição o quanto antes para evitar a falta do produto e possíveis impactos nas vendas.'),
                        usuarios=Usuario.objects.filter(empresa=p.vinc_emp, receber_alerta_estoque=True, filial_user__estoque__ativar_alerta_estoque=True), remetente=p,
                        verb='Estoque mínimo', dados={'produto': p.codigo, 'estoque': estoque.codigo}
                    )
                else:
                    resolver_alerta(empresa=p.vinc_emp, tipo='ESTOQUE_MINIMO', referencia=p.codigo)
                # ALERTA DE ESTOQUE MÁXIMO
                if (saldo.estoque_maximo > 0 and saldo.quantidade >= saldo.estoque_maximo):
                    quantidade_alerta = (int(saldo.quantidade) if saldo.quantidade == int(saldo.quantidade) else saldo.quantidade)
                    criar_alerta(empresa=p.vinc_emp, tipo='ESTOQUE_MAXIMO', referencia=p.codigo, titulo='Alerta de Estoque Máximo',
                        descricao=(f'Atenção! O produto ({p.desc_prod}) atingiu o estoque máximo configurado, totalizando {quantidade_alerta} unidades disponíveis no estoque '
                            f'{estoque.descricao}. Recomendamos organizar os produtos que sobraram para evitar desperdícios de mercadorias.'),
                        usuarios=Usuario.objects.filter(empresa=p.vinc_emp, receber_alerta_estoque=True, filial_user__estoque__ativar_alerta_estoque=True), remetente=p,
                        verb='Estoque máximo', dados={'produto': p.codigo, 'estoque': estoque.codigo}
                    )
                else:
                    resolver_alerta(empresa=p.vinc_emp, tipo='ESTOQUE_MAXIMO', referencia=p.codigo)
            # TABELAS DE PREÇO
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
                if not tabela_id or not vl_prod: continue
                try: tabela = TabelaPreco.objects.get(codigo=tabela_id, vinc_emp=empresa)
                except TabelaPreco.DoesNotExist:
                    messages.warning(request, f"Tabela {tabela_id} não encontrada.")
                    continue
                try: vl_prod_decimal = parse_decimal(vl_prod)
                except Exception: vl_prod_decimal = Decimal('0.00')
                try: margem_decimal = parse_decimal(margem)
                except Exception: margem_decimal = Decimal('0.00')
                ProdutoTabela.objects.create(produto=p, tabela=tabela, vl_prod=vl_prod_decimal, margem=margem_decimal)
            # CÓDIGOS SECUNDÁRIOS
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
                if not codigo: continue
                if CodigoProduto.objects.filter(codigo=codigo, produto__vinc_emp=empresa).exists():
                    messages.warning(request, f"O código '{codigo}' já está vinculado a outro produto desta empresa.")
                    continue
                CodigoProduto.objects.create(produto=p, codigo=codigo, vinc_emp=empresa)
            # LOG
            registrar_log(request, "CRIAR", "Produto", p.desc_prod, f"Adicionou o produto: {p.codigo} - {p.desc_prod}", p.id, gerar_alteracoes(obj_novo=p))
            messages.success(request, 'Produto adicionado com sucesso!')
            return redirect(f'/produtos/lista/?tp=cod&s={p.codigo}')
    except ObjectDoesNotExist: error_messages.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        detalhe = str(e.__cause__ if e.__cause__ else e)
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {detalhe}")
    except DatabaseError as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except ValueError as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return render(request, 'produtos/add_produto.html', {'form': form, 'error_messages': error_messages, 'filiais': filiais})

@login_required
def att_produto(request, codigo):
    error_messages = []
    empresa = request.user.empresa
    filiais = Filial.objects.filter(vinc_emp=empresa)
    p = get_object_or_404(Produto, codigo=codigo, vinc_emp=empresa)
    it_old = Produto.objects.get(codigo=p.codigo, vinc_emp=empresa)
    todas_tabelas = TabelaPreco.objects.none()
    prod_tabelas = ProdutoTabela.objects.none()
    saldos_estoque = SaldoEstoque.objects.filter(produto=p, estoque__empresa=empresa).select_related('estoque', 'estoque__filial')
    if not request.user.has_perm('produtos.change_produto'):
        messages.info(request, 'Você não tem permissão para editar produtos.')
        return redirect('/produtos/lista/')
    # GET
    if request.method != 'POST':
        form = ProdutoForm(instance=p, empresa=empresa)
        todas_tabelas = TabelaPreco.objects.filter(vinc_emp=empresa)
        prod_tabelas = (p.produtotabela_set.select_related('tabela').filter(tabela__vinc_emp=empresa))
        return render(request, 'produtos/att_produto.html', {'form': form, 'p': p, 'tabelas': todas_tabelas, 'filiais': filiais, 'saldos_estoque': saldos_estoque,
            'prod_tabelas': prod_tabelas, 'codigos': p.codigos.all(), 'error_messages': error_messages,
        })
    # POST
    form = ProdutoForm(request.POST, instance=p, empresa=empresa)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'produtos/att_produto.html', {'form': form, 'p': p, 'error_messages': error_messages, 'filiais': filiais, 'saldos_estoque': saldos_estoque})
    try:
        with transaction.atomic():
            # PRODUTO
            lista_orc = request.POST.get('lista_orc') == 'on'
            p = form.save(commit=False)
            # Garante que continue na empresa do usuário
            p.vinc_emp = empresa
            p.lista_orc = lista_orc
            # Os campos antigos de estoque não serão mais utilizados. O estoque real será controlado pelo SaldoEstoque.
            p.estoque_prod = Decimal('0.00')
            p.estoque_minimo = Decimal('0.00')
            p.estoque_maximo = Decimal('0.00')
            p.save()
            # ESTOQUES / SALDO ESTOQUE
            estoque_dict = {}
            for key, value in request.POST.items():
                if key.startswith("estoque["):
                    m = re.match(r"estoque\[(\d+)\]\[(\w+)\]", key)
                    if m:
                        idx, campo = m.groups()
                        if idx not in estoque_dict:
                            estoque_dict[idx] = {}
                        estoque_dict[idx][campo] = value
            # IDs dos saldos que continuam vinculados ao produto
            saldo_ids = []
            for dados in estoque_dict.values():
                estoque_id = dados.get("estoque")
                if not estoque_id: continue
                # Localiza o estoque da empresa
                try: estoque = (Estoque.objects.select_related('filial').get(codigo=estoque_id, empresa=empresa))
                except Estoque.DoesNotExist:
                    messages.warning(request, f"Estoque {estoque_id} não encontrado.")
                    continue
                # Valida a filial enviada
                filial_id = dados.get("filial")
                if filial_id:
                    if str(estoque.filial.codigo) != str(filial_id): raise ValueError(f'O estoque "{estoque.descricao}" não pertence à filial selecionada.')
                # Converte valores
                try: quantidade = (parse_decimal(dados.get("quantidade")) or Decimal('0.000'))
                except Exception: quantidade = Decimal('0.000')
                try: estoque_minimo = (parse_decimal(dados.get("estoque_minimo")) or Decimal('0.000'))
                except Exception: estoque_minimo = Decimal('0.000')
                try: estoque_maximo = (parse_decimal(dados.get("estoque_maximo")) or Decimal('0.000'))
                except Exception: estoque_maximo = Decimal('0.000')
                # Validações
                if quantidade < 0: raise ValueError(f'A quantidade do estoque "{estoque.descricao}" não pode ser negativa.')
                if estoque_minimo < 0: raise ValueError(f'O estoque mínimo do estoque "{estoque.descricao}" não pode ser negativo.')
                if estoque_maximo < 0: raise ValueError(f'O estoque máximo do estoque "{estoque.descricao}" não pode ser negativo.')
                if (estoque_maximo > 0 and estoque_minimo > estoque_maximo):
                    raise ValueError(f'O estoque mínimo do estoque "{estoque.descricao}" não pode ser maior que o estoque máximo.')
                # Procura saldo existente
                saldo = (SaldoEstoque.objects.select_for_update().filter(estoque=estoque, produto=p).first())
                # SALDO EXISTENTE
                if saldo:
                    quantidade_atual = saldo.quantidade
                    # Ajusta a quantidade através do serviço
                    # Nunca fazemos:
                    # saldo.quantidade = quantidade
                    # pois isso apagaria o histórico da alteração. O ajustar_estoque cria o movimento AJUSTE.
                    if quantidade != quantidade_atual:
                        ajustar_estoque(estoque=estoque, produto=p, nova_quantidade=quantidade, usuario=request.user, descricao=(f'Ajuste de estoque na alteração do produto {p.codigo}'))
                        saldo.refresh_from_db()
                    # Atualiza mínimo e máximo
                    saldo.estoque_minimo = estoque_minimo
                    saldo.estoque_maximo = estoque_maximo
                    saldo.save(update_fields=['estoque_minimo', 'estoque_maximo', 'data_atualizacao'])
                # NOVO SALDO
                else:
                    saldo = SaldoEstoque.objects.create(estoque=estoque, produto=p, quantidade=Decimal('0.000'), estoque_minimo=estoque_minimo, estoque_maximo=estoque_maximo)
                    # Estoque inicial
                    if quantidade > 0:
                        adicionar_estoque(estoque=estoque, produto=p, quantidade=quantidade, usuario=request.user,
                            descricao=(f'Cadastro de estoque do produto {p.codigo} - estoque inicial')
                        )
                        saldo.refresh_from_db()
                # Guarda o saldo que continua no formulário
                saldo_ids.append(saldo.id)
                # ALERTA DE ESTOQUE MÍNIMO
                if (saldo.estoque_minimo > 0 and saldo.quantidade <= saldo.estoque_minimo):
                    quantidade_alerta = (int(saldo.quantidade) if saldo.quantidade == int(saldo.quantidade) else saldo.quantidade)
                    criar_alerta(empresa=p.vinc_emp, tipo='ESTOQUE_MINIMO', referencia=p.codigo, titulo='Alerta de Estoque mínimo',
                        descricao=(f'Atenção! O produto ({p.desc_prod}) atingiu o estoque mínimo configurado e possui apenas {quantidade_alerta} unidades disponíveis no estoque '
                            f'{estoque.descricao}. Recomendamos realizar a reposição o quanto antes para evitar a falta do produto e possíveis impactos nas vendas.'
                        ),
                        usuarios=Usuario.objects.filter(empresa=p.vinc_emp, receber_alerta_estoque=True, filial_user__estoque__ativar_alerta_estoque=True), remetente=p,
                        verb='Estoque mínimo', dados={'produto': p.codigo, 'estoque': estoque.codigo}
                    )
                else:
                    resolver_alerta(empresa=p.vinc_emp, tipo='ESTOQUE_MINIMO', referencia=p.codigo)
                # ALERTA DE ESTOQUE MÁXIMO
                if (saldo.estoque_maximo > 0 and saldo.quantidade >= saldo.estoque_maximo):
                    quantidade_alerta = (int(saldo.quantidade) if saldo.quantidade == int(saldo.quantidade) else saldo.quantidade)
                    criar_alerta(empresa=p.vinc_emp, tipo='ESTOQUE_MAXIMO', referencia=p.codigo, titulo='Alerta de Estoque Máximo',
                        descricao=(f'Atenção! O produto ({p.desc_prod}) atingiu o estoque máximo configurado, totalizando {quantidade_alerta} unidades disponíveis no estoque '
                            f'{estoque.descricao}. Recomendamos organizar os produtos que sobraram para evitar desperdícios de mercadorias.'),
                        usuarios=Usuario.objects.filter(empresa=p.vinc_emp, receber_alerta_estoque_maximo=True, filial_user__estoque__ativar_alerta_estoque=True), remetente=p,
                        verb='Estoque máximo', dados={'produto': p.codigo, 'estoque': estoque.codigo}
                    )
                else:
                    resolver_alerta(empresa=p.vinc_emp, tipo='ESTOQUE_MAXIMO', referencia=p.codigo)
            # REMOVE SALDOS QUE NÃO ESTÃO MAIS NO FORMULÁRIO
            # NÃO apagamos saldo que possua movimentações.
            # Se o usuário removeu uma linha do formulário:
            # - se nunca houve movimento, podemos remover;
            # - se já possui histórico, mantemos o saldo.
            # Isso evita perder a relação com o histórico de MovimentoEstoque.
            saldos_remover = (SaldoEstoque.objects.filter(produto=p, estoque__empresa=empresa).exclude(id__in=saldo_ids))
            for saldo_remover in saldos_remover:
                possui_movimento = MovimentoEstoque.objects.filter(produto=p, estoque=saldo_remover.estoque).exists()
                if not possui_movimento:
                    saldo_remover.delete()
            # TABELAS DE PREÇO
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
                    tabela = TabelaPreco.objects.get(codigo=tabela_id, vinc_emp=empresa)
                except TabelaPreco.DoesNotExist:
                    messages.warning(request, f"Tabela {tabela_id} não encontrada.")
                    continue
                vl_prod_decimal = parse_decimal(vl_prod)
                margem_decimal = parse_decimal(margem)
                ep, _ = ProdutoTabela.objects.update_or_create(produto=p, tabela=tabela, defaults={'vl_prod': vl_prod_decimal, 'margem': margem_decimal})
                tab_preco_ids.append(ep.id)
            # Remove tabelas antigas não reenviadas, somente da empresa atual
            ProdutoTabela.objects.filter(produto=p, tabela__vinc_emp=empresa).exclude(id__in=tab_preco_ids).delete()
            # CÓDIGOS SECUNDÁRIOS
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
                codigo_secundario = (dados.get("codigo", "").strip())
                if not codigo_secundario:
                    continue
                # Verifica se já existe em outro produto da mesma empresa
                if (CodigoProduto.objects.filter(codigo=codigo_secundario, produto__vinc_emp=empresa).exclude(produto=p).exists()):
                    messages.warning(request, f"O código '{codigo_secundario}' já está vinculado a outro produto desta empresa.")
                    continue
                ep, _ = CodigoProduto.objects.get_or_create(produto=p, codigo=codigo_secundario, vinc_emp=empresa)
                cod_sec_ids.append(ep.id)
            # Remove códigos antigos não reenviados
            CodigoProduto.objects.filter(produto=p).exclude(codigo__in=cod_sec_ids).delete()
            # LOG
            registrar_log(request, "ALTERAR", "Produto", p.desc_prod, f"Alterou o produto: {p.codigo} - {p.desc_prod}", p.id, gerar_alteracoes(it_old, p))
            messages.success(request, 'Produto atualizado com sucesso!')
            next_url = (request.POST.get('next') or request.GET.get('next'))
            if next_url:
                return redirect(next_url)
            return redirect(f'/produtos/lista/?tp=cod&s={p.codigo}')
    # TRATAMENTO DE ERROS
    except ObjectDoesNotExist: error_messages.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        detalhe = str(e.__cause__ if e.__cause__ else e)
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {detalhe}")
    except DatabaseError as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except ValueError as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> {str(e)}")
    except Exception as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    # RENDER APÓS ERRO
    todas_tabelas = TabelaPreco.objects.filter(vinc_emp=empresa)
    prod_tabelas = (p.produtotabela_set.select_related('tabela').filter(tabela__vinc_emp=empresa))
    saldos_estoque = (SaldoEstoque.objects.filter(produto=p, estoque__empresa=empresa).select_related('estoque', 'estoque__filial'))
    return render(request,'produtos/att_produto.html',{'form':form,'p':p,'tabelas':todas_tabelas,'filiais':filiais,'saldos_estoque':saldos_estoque,'prod_tabelas':prod_tabelas,
        'codigos': p.codigos.all() if p else [], 'error_messages': error_messages
    })

@login_required
def clonar_produto(request, codigo):
    error_messages = []
    empresa = request.user.empresa
    filiais = Filial.objects.filter(vinc_emp=empresa)
    p = get_object_or_404(Produto, codigo=codigo, vinc_emp=empresa)
    todas_tabelas = TabelaPreco.objects.none()
    prod_tabelas = ProdutoTabela.objects.none()
    if not request.user.has_perm('produtos.clonar_produto'):
        messages.info(request, 'Você não tem permissão para clonar produtos.')
        return redirect('/produtos/lista/')
    if request.method != 'POST':
        form = ProdutoForm(instance=p, empresa=empresa)
        todas_tabelas = TabelaPreco.objects.filter(vinc_emp=empresa)
        prod_tabelas = p.produtotabela_set.select_related('tabela').filter(tabela__vinc_emp=empresa)
        return render(request, 'produtos/clonar.html', {'form': form, 'p': p, 'tabelas': todas_tabelas, 'filiais': filiais, 'prod_tabelas': prod_tabelas, 'codigos': p.codigos.all(),
            'error_messages': error_messages
        })
    post_data = request.POST.copy()
    form = ProdutoForm(post_data, empresa=empresa)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'produtos/clonar.html', {'form': form, 'p': p, 'error_messages': error_messages, 'filiais': filiais})
    try:
        with transaction.atomic():
            lista_orc = post_data.get('lista_orc') == 'on'
            novo_produto = form.save(commit=False)
            if novo_produto.unidProd and novo_produto.unidProd.vinc_emp != empresa: return HttpResponseForbidden()
            if novo_produto.grupo and novo_produto.grupo.vinc_emp != empresa: return HttpResponseForbidden()
            if novo_produto.marca and novo_produto.marca.vinc_emp != empresa: return HttpResponseForbidden()
            novo_produto.vinc_emp = empresa
            novo_produto.lista_orc = lista_orc
            novo_produto.estoque_prod = Decimal('0.00')
            novo_produto.estoque_minimo = Decimal('0.00')
            novo_produto.estoque_maximo = Decimal('0.00')
            novo_produto.save()
            # ESTOQUES / SALDO ESTOQUE
            estoque_dict = {}
            for key, value in request.POST.items():
                if key.startswith("estoque["):
                    m = re.match(r"estoque\[(\d+)\]\[(\w+)\]", key)
                    if m:
                        idx, campo = m.groups()
                        if idx not in estoque_dict:
                            estoque_dict[idx] = {}
                        estoque_dict[idx][campo] = value
            for dados in estoque_dict.values():
                estoque_id = dados.get("estoque")
                if not estoque_id:
                    continue
                try:
                    estoque = Estoque.objects.get(codigo=estoque_id, empresa=empresa)
                except Estoque.DoesNotExist:
                    messages.warning(request, f"Estoque {estoque_id} não encontrado.")
                    continue
                # Quantidade inicial
                try:
                    quantidade = (parse_decimal(dados.get("quantidade")) or Decimal('0.000'))
                except Exception:
                    quantidade = Decimal('0.000')
                # Estoque mínimo
                try:
                    estoque_minimo = (parse_decimal(dados.get("estoque_minimo")) or Decimal('0.000'))
                except Exception:
                    estoque_minimo = Decimal('0.000')
                # Estoque máximo
                try:
                    estoque_maximo = (parse_decimal(dados.get("estoque_maximo")) or Decimal('0.000'))
                except Exception:
                    estoque_maximo = Decimal('0.000')
                # Validações
                if quantidade < 0:
                    raise ValueError(f'A quantidade do estoque "{estoque.descricao}" não pode ser negativa.')
                if estoque_minimo < 0:
                    raise ValueError(f'O estoque mínimo do estoque "{estoque.descricao}" não pode ser negativo.')
                if estoque_maximo < 0:
                    raise ValueError(f'O estoque máximo do estoque "{estoque.descricao}" não pode ser negativo.')
                if (estoque_maximo > 0 and estoque_minimo > estoque_maximo):
                    raise ValueError(f'O estoque mínimo do estoque "{estoque.descricao}" não pode ser maior que o estoque máximo.')
                # Cria o saldo
                saldo = SaldoEstoque.objects.create(estoque=estoque, produto=novo_produto, quantidade=Decimal('0.000'), estoque_minimo=estoque_minimo, estoque_maximo=estoque_maximo)
                # Estoque inicial
                if quantidade > 0:
                    adicionar_estoque(estoque=estoque, produto=novo_produto, quantidade=quantidade, usuario=request.user,
                        descricao=(f'Clonagem do produto {p.codigo} para o produto {novo_produto.codigo} - estoque inicial')
                    )
                    saldo.refresh_from_db()
                # ALERTA DE ESTOQUE MÍNIMO
                if (saldo.estoque_minimo > 0 and saldo.quantidade <= saldo.estoque_minimo):
                    quantidade_alerta = (int(saldo.quantidade) if saldo.quantidade == int(saldo.quantidade) else saldo.quantidade)
                    criar_alerta(empresa=novo_produto.vinc_emp, tipo='ESTOQUE_MINIMO', referencia=novo_produto.codigo, titulo='Alerta de Estoque mínimo',
                        descricao=(f'Atenção! O produto ({novo_produto.desc_prod}) atingiu o estoque mínimo configurado e possui apenas {quantidade_alerta} unidades disponíveis '
                            f'no estoque {estoque.descricao}. Recomendamos realizar a reposição o quanto antes para evitar a falta do produto e possíveis impactos nas vendas.'),
                        usuarios=Usuario.objects.filter(empresa=novo_produto.vinc_emp, receber_alerta_estoque=True, filial_user__estoque__ativar_alerta_estoque=True),
                        remetente=novo_produto, verb='Estoque mínimo', dados={'produto': novo_produto.codigo, 'estoque': estoque.codigo}
                    )
                else:
                    resolver_alerta(empresa=novo_produto.vinc_emp, tipo='ESTOQUE_MINIMO', referencia=novo_produto.codigo)
                # ALERTA DE ESTOQUE MÁXIMO
                if (saldo.estoque_maximo > 0 and saldo.quantidade >= saldo.estoque_maximo):
                    quantidade_alerta = (int(saldo.quantidade) if saldo.quantidade == int(saldo.quantidade) else saldo.quantidade)
                    criar_alerta(empresa=novo_produto.vinc_emp, tipo='ESTOQUE_MAXIMO', referencia=novo_produto.codigo, titulo='Alerta de Estoque Máximo',
                        descricao=(f'Atenção! O produto ({novo_produto.desc_prod}) atingiu o estoque máximo configurado, totalizando {quantidade_alerta} unidades '
                            f'disponíveis no estoque {estoque.descricao}. Recomendamos organizar os produtos que sobraram para evitar desperdícios de mercadorias.'),
                        usuarios=Usuario.objects.filter(empresa=novo_produto.vinc_emp, receber_alerta_estoque_maximo=True, filial_user__estoque__ativar_alerta_estoque=True),
                        remetente=novo_produto, verb='Estoque máximo', dados={'produto': novo_produto.codigo, 'estoque': estoque.codigo}
                    )
                else:
                    resolver_alerta(empresa=novo_produto.vinc_emp, tipo='ESTOQUE_MAXIMO', referencia=novo_produto.codigo)
            tab_preco_dict = {}
            for key, value in request.POST.items():
                if key.startswith("tab_preco["):
                    m = re.match(r"tab_preco\[(\d+)\]\[(\w+)\]", key)
                    if m:
                        idx, campo = m.groups()
                        if idx not in tab_preco_dict: tab_preco_dict[idx] = {}
                        tab_preco_dict[idx][campo] = value
            tab_preco_ids = []
            for dados in tab_preco_dict.values():
                tabela_id = dados.get("tabela")
                margem = dados.get("margem")
                vl_prod = dados.get("vl_prod")
                if not tabela_id or not vl_prod: continue
                try: tabela = TabelaPreco.objects.get(codigo=tabela_id, vinc_emp=empresa)
                except TabelaPreco.DoesNotExist:
                    messages.warning(request, f"Tabela {tabela_id} não encontrada.")
                    continue
                vl_prod_decimal = parse_decimal(vl_prod)
                margem_decimal = parse_decimal(margem)
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
                        if idx not in cod_sec_dict: cod_sec_dict[idx] = {}
                        cod_sec_dict[idx][campo] = value
            for dados in cod_sec_dict.values():
                codigo = dados.get("codigo", "").strip()
                if not codigo: continue
                # Verifica se já existe esse código em outro produto da mesma empresa
                if CodigoProduto.objects.filter(codigo=codigo, produto__vinc_emp=empresa).exists():
                    messages.warning(request, f"O código '{codigo}' já está vinculado a outro produto desta empresa.")
                    continue
                # Cria o código somente se ele foi informado manualmente no clone
                CodigoProduto.objects.create(produto=novo_produto, codigo=codigo, vinc_emp=empresa)
            registrar_log(
                request, "CRIAR", "Produto", novo_produto.desc_prod,
                f"Adicionou o produto: {novo_produto.codigo} - {novo_produto.desc_prod} apartir da clonagem do produto: {p.codigo}",
                novo_produto.id, gerar_alteracoes(obj_novo=novo_produto)
            )
            messages.success(request, 'Produto clonado com sucesso!')
            return redirect(f'/produtos/lista/?tp=cod&s={novo_produto.codigo}')
    except ObjectDoesNotExist: error_messages.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        detalhe = str(e.__cause__ if e.__cause__ else e)
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {detalhe}")
    except DatabaseError as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except ValueError as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> {str(e)}")
    except Exception as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    todas_tabelas = TabelaPreco.objects.filter(vinc_emp=empresa)
    prod_tabelas = p.produtotabela_set.select_related('tabela').filter(tabela__vinc_emp=empresa)
    return render(request,'produtos/clonar.html',{'form':form,'p':p,'tabelas':todas_tabelas,'filiais':filiais,'prod_tabelas':prod_tabelas,'codigos':p.codigos.all() if p else [],
        'error_messages': error_messages
    })

@login_required
def del_produto(request, codigo):
    if not request.user.has_perm('produtos.delete_produto'):
        messages.info(request, 'Você não tem permissão para deletar produtos.')
        return redirect('lista-produtos')
    try:
        with transaction.atomic():
            p = get_object_or_404(Produto, codigo=codigo, vinc_emp=request.user.empresa)
            registrar_log(request, "EXCLUIR", "Produto", p.desc_prod, f"Excluiu o produto: {p.codigo} - {p.desc_prod}", p.id, gerar_alteracoes(obj_antigo=p))
            p.delete()
        messages.success(request, 'Produto deletado com sucesso!')
        return redirect(reverse('lista-produtos'))
    except ObjectDoesNotExist: messages.error(request, "<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        detalhe = str(e.__cause__ if e.__cause__ else e)
        messages.error(request, f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {detalhe}")
    except DatabaseError as e: messages.error(request, f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except ValueError as e: messages.error(request, f"<i class='fa-solid fa-xmark'></i> {str(e)}")
    except Exception as e: messages.error(request, f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return redirect('/produtos/lista/')