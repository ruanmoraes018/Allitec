from datetime import datetime, date
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from util.permissoes import verifica_permissao, verifica_alguma_permissao
from decimal import Decimal, InvalidOperation
from django.views.decorators.http import require_POST
from filiais.models import Filial
from .models import Entrada, EntradaProduto, EntradaProdutoTabela
from .forms import EntradaForm
from django.db import IntegrityError, DatabaseError, transaction
from django.core.exceptions import ObjectDoesNotExist
import re
import xml.etree.ElementTree as ET
from produtos.models import Produto, ProdutoFornecedor, CodigoProduto, ProdutoTabela
from fornecedores.models import Fornecedor
from unidades.models import Unidade
from marcas.models import Marca
from grupos.models import Grupo
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado
from tabelas_preco.models import TabelaPreco
import json
from django.db.models import Q

def parse_decimal(value):
    if value is None or value == "": return Decimal("0")
    try: return Decimal(str(value).replace(",", "."))
    except InvalidOperation: return Decimal("0")

@verifica_permissao('entradas.view_entrada')
@login_required
def lista_entradas(request):
    s = request.GET.get('s')
    f_s = request.GET.get('sit')
    tp_dt = request.GET.get('tp_dt')
    dt_ini = request.GET.get('dt_ini')
    dt_fim = request.GET.get('dt_fim')
    por_dt = request.GET.get('p_dt')
    forn = request.GET.get('forn')
    fil = request.GET.get('fil')
    reg = request.GET.get('reg', '10')
    hoje = datetime.today()
    empresa = request.user.empresa
    entradas = Entrada.objects.filter(vinc_emp=empresa).prefetch_related("itens__produto")
    if s: entradas = entradas.filter(numeracao__icontains=s).order_by('numeracao')
    # Filtro por data
    if por_dt == 'Sim' and dt_ini and dt_fim:
        try:
            # Converter as datas de entrada de string para date
            dt_ini_dt = datetime.strptime(dt_ini, '%d/%m/%Y').date()
            dt_fim_dt = datetime.strptime(dt_fim, '%d/%m/%Y').date()
            if tp_dt == 'Emissão': entradas = entradas.filter(dt_emi__range=(dt_ini_dt, dt_fim_dt))
            elif tp_dt == 'Entrega': entradas = entradas.filter(dt_ent__range=(dt_ini_dt, dt_fim_dt))
        except ValueError: entradas = Entrada.objects.none()
    # Apenas aplica o filtro do dia atual se nenhum filtro estiver ativo
    filtros_ativos = any([s, f_s, por_dt == 'Sim', forn, tp_dt and tp_dt != 'Todos'])
    if not filtros_ativos: entradas = entradas.filter(dt_emi=hoje, situacao='Pendente')
    # Filtro por situação
    if f_s and f_s != 'Todos': entradas = entradas.filter(situacao=f_s)
    # Filtro por cliente
    if forn: entradas = entradas.filter(fornecedor_id=forn)
    if fil: entradas = entradas.filter(vinc_fil_id=fil)
    fornecedores = Fornecedor.objects.filter(vinc_emp=request.user.empresa)
    filiais = Filial.objects.filter(vinc_emp=request.user.empresa)
    # Paginação
    if reg == 'todos': num_pagina = entradas.count() or 1
    else:
        try: num_pagina = int(reg) if int(reg) > 0 else 10
        except ValueError: num_pagina = 10
    paginator = Paginator(entradas, num_pagina)
    page = request.GET.get('page')
    entradas = paginator.get_page(page)
    return render(request, 'entradas/lista.html', {'entradas': entradas, 's': s, 'forn': forn, 'fil': fil, 'fornecedores': fornecedores, 'filiais': filiais, 'dt_ini': dt_ini, 'dt_fim': dt_fim, 'p_dt': por_dt, 'tp_dt': tp_dt, 'reg': reg})

@login_required
def entradas_por_produto(request, produto_id):
    entradas = EntradaProduto.objects.filter(produto_id=produto_id, vinc_emp=request.user.empresa).select_related('entrada', 'entrada__fornecedor')
    data = []
    for ep in entradas:
        entrada = ep.entrada
        data.append({'entrada_id': entrada.id, 'data': entrada.dt_ent.strftime('%d/%m/%Y') if entrada.dt_ent else '', 'fornecedor': str(entrada.fornecedor), 'quantidade': float(ep.quantidade), 'valor_unitario': float(ep.preco_unitario), 'total_entrada': float(entrada.total)})
    return JsonResponse({'entradas': data})

def somente_numeros(valor):
    return re.sub(r'\D', '', str(valor or ''))

def text(node, path, ns=None, default=''):
    if node is None:
        return default
    el = node.find(path, ns or {})
    return el.text.strip() if el is not None and el.text else default

def formatar_decimal_en(valor):
    if valor is None:
        return "0.00"
    return f"{float(valor):.2f}"

def parse_nfe_xml(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

    infNFe = root.find('.//nfe:infNFe', ns)
    if infNFe is None:
        raise ValueError('XML inválido: infNFe não encontrada.')

    ide = infNFe.find('nfe:ide', ns)
    emit = infNFe.find('nfe:emit', ns)
    total = infNFe.find('nfe:total/nfe:ICMSTot', ns)

    dados = {
        'chave': '',
        'numero': text(ide, 'nfe:nNF', ns),
        'serie': text(ide, 'nfe:serie', ns),
        'data_emissao': text(ide, 'nfe:dhEmi', ns) or text(ide, 'nfe:dEmi', ns),
        'nat_op': text(ide, 'nfe:natOp', ns),
        'modelo': text(ide, 'nfe:mod', ns),
        'fornecedor': {
            'cnpj': somente_numeros(text(emit, 'nfe:CNPJ', ns)),
            'cpf': somente_numeros(text(emit, 'nfe:CPF', ns)),
            'nome': text(emit, 'nfe:xNome', ns),
            'fantasia': text(emit, 'nfe:xFant', ns),
            'ie': text(emit, 'nfe:IE', ns),
        },
        'total_nota': parse_decimal(text(total, 'nfe:vNF', ns)),
        'itens': []
    }

    if 'Id' in infNFe.attrib:
        dados['chave'] = infNFe.attrib['Id'].replace('NFe', '')

    for det in infNFe.findall('nfe:det', ns):
        prod = det.find('nfe:prod', ns)
        if prod is None:
            continue

        item = {
            'codigo_fornecedor': text(prod, 'nfe:cProd', ns),
            'ean': text(prod, 'nfe:cEAN', ns),
            'descricao': text(prod, 'nfe:xProd', ns),
            'ncm': text(prod, 'nfe:NCM', ns),
            'cfop': text(prod, 'nfe:CFOP', ns),
            'unidade': text(prod, 'nfe:uCom', ns),
            'quantidade': parse_decimal(text(prod, 'nfe:qCom', ns)),
            'valor_unitario': parse_decimal(text(prod, 'nfe:vUnCom', ns)),
            'subtotal': parse_decimal(text(prod, 'nfe:vProd', ns)),
            'desconto': parse_decimal(text(prod, 'nfe:vDesc', ns, '0')),
            'marca': '',
        }
        dados['itens'].append(item)

    return dados


def parse_data_xml_para_input(data_str):
    if not data_str:
        return ''
    try:
        if 'T' in data_str:
            return datetime.fromisoformat(data_str[:19]).date().isoformat()
        return datetime.strptime(data_str[:10], '%Y-%m-%d').date().isoformat()
    except Exception:
        return ''

def to_decimal(valor, default="0.00"):
    try:
        return Decimal(str(valor or default).replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)

def formatar_data_br(data_iso):
    if not data_iso:
        return ""
    try:
        dt = datetime.fromisoformat(data_iso.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except:
        return ""

def formatar_data_input(data_iso):
    if not data_iso:
        return ""
    try:
        dt = datetime.fromisoformat(data_iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except:
        return ""

@login_required
@require_POST
def ler_xml_entrada(request):
    empresa = request.user.empresa
    arquivo = request.FILES.get("xml")
    if not arquivo:
        return JsonResponse({"ok": False, "erro": "Arquivo XML não enviado."}, status=400)
    try:
        tree = ET.parse(arquivo)
        root = tree.getroot()
        ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
        ide = root.find(".//nfe:ide", ns)
        emit = root.find(".//nfe:emit", ns)
        total = root.find(".//nfe:total/nfe:ICMSTot", ns)
        infNFe = root.find(".//nfe:infNFe", ns)
        chNFe = root.find(".//nfe:protNFe/nfe:infProt/nfe:chNFe", ns)
        dh_emi = get_text(ide, "nfe:dhEmi", ns)
        valor_total_nota = to_decimal(get_text(total, "nfe:vNF", ns))
        fornecedor_doc = somente_numeros(get_text(emit, "nfe:CNPJ", ns) or get_text(emit, "nfe:CPF", ns))
        fornecedor = Fornecedor.objects.filter(vinc_emp=empresa, cpf_cnpj=fornecedor_doc).first()
        itens_payload = []
        for det in root.findall(".//nfe:det", ns):
            prod = det.find("nfe:prod", ns)
            if prod is None:
                continue
            codigo_fornecedor = get_text(prod, "nfe:cProd", ns)
            descricao = get_text(prod, "nfe:xProd", ns)
            unidade = get_text(prod, "nfe:uCom", ns)
            ean = get_text(prod, "nfe:cEAN", ns)
            ncm = get_text(prod, "nfe:NCM", ns)
            cfop = get_text(prod, "nfe:CFOP", ns)
            cest = get_text(prod, "nfe:CEST", ns)
            info_adicional = get_text(det, "nfe:infAdProd", ns)
            quantidade = to_decimal(get_text(prod, "nfe:qCom", ns))
            valor_unitario = to_decimal(get_text(prod, "nfe:vUnCom", ns))
            subtotal = to_decimal(get_text(prod, "nfe:vProd", ns))
            desconto = to_decimal(get_text(prod, "nfe:vDesc", ns, "0"))
            produto_vinculado = None
            if fornecedor and codigo_fornecedor:
                vinculo = ProdutoFornecedor.objects.filter(vinc_emp=empresa, fornecedor=fornecedor, codigo_fornecedor=codigo_fornecedor).select_related("produto").first()
                if vinculo:
                    produto_vinculado = vinculo.produto
            if not produto_vinculado and ean and ean not in ["SEM GTIN", "SEMGTIN"]:
                cod_obj = CodigoProduto.objects.filter(vinc_emp=empresa, codigo=ean).select_related("produto").first()
                if cod_obj:
                    produto_vinculado = cod_obj.produto
            candidatos_ids = set()
            if ean and ean not in ["SEM GTIN", "SEMGTIN"]:
                candidatos_ids.update(CodigoProduto.objects.filter(vinc_emp=empresa, codigo=ean).values_list("produto_id", flat=True))
            if descricao:
                trecho = descricao[:30]
                candidatos_ids.update(Produto.objects.filter(vinc_emp=empresa).filter(Q(desc_prod__icontains=trecho) | Q(desc_normalizado__icontains=trecho.lower())).values_list("id", flat=True)[:10])
            candidatos = list(Produto.objects.filter(vinc_emp=empresa, id__in=candidatos_ids).values("id", "desc_prod")[:10])
            itens_payload.append({
                "codigo_fornecedor": codigo_fornecedor, "descricao": descricao, "unidade": unidade, "ncm": ncm, "cfop": cfop, "cest": cest, "info_adicional": info_adicional, "ean": ean, "quantidade": formatar_decimal_en(quantidade),
                "valor_unitario": formatar_decimal_en(valor_unitario), "desconto": formatar_decimal_en(desconto), "subtotal": formatar_decimal_en(subtotal),
                "produto_vinculado": {"id": produto_vinculado.id, "descricao": produto_vinculado.desc_prod} if produto_vinculado else None, "candidatos": candidatos,
            })
        return JsonResponse({
            "ok": True,
            "nota": {"numero": get_text(ide, "nfe:nNF", ns), "serie": get_text(ide, "nfe:serie", ns), "data_emissao": formatar_data_br(dh_emi), "data_emissao_input": formatar_data_input(dh_emi),
                "nat_op": get_text(ide, "nfe:natOp", ns), "modelo": get_text(ide, "nfe:mod", ns), "chave": chNFe.text if chNFe is not None and chNFe.text else (
                    infNFe.attrib.get("Id", "").replace("NFe", "") if infNFe is not None else ""
                ), "total": formatar_decimal_en(valor_total_nota),
            },
            "fornecedor": {"id": fornecedor.id if fornecedor else None, "existe": bool(fornecedor), "cpf_cnpj": fornecedor_doc, "razao_social": get_text(emit, "nfe:xNome", ns), "fantasia": get_text(emit, "nfe:xFant", ns),
                "ie": get_text(emit, "nfe:IE", ns),
            }, "itens": itens_payload
        })

    except Exception as e:
        return JsonResponse({"ok": False, "erro": f"Erro ao ler XML: {str(e)}"}, status=400)

def get_text(node, path, ns, default=""):
    el = node.find(path, ns)
    return el.text.strip() if el is not None and el.text else default

def get_or_create_estado(empresa, uf_sigla):
    if not uf_sigla:
        return None
    return Estado.objects.filter(vinc_emp=empresa, nome_estado__iexact=uf_sigla).first()

def get_or_create_cidade(empresa, nome_cidade):
    if not nome_cidade:
        return None
    cidade = Cidade.objects.filter(vinc_emp=empresa, nome_cidade__iexact=nome_cidade).first()
    if cidade:
        return cidade
    return Cidade.objects.create(vinc_emp=empresa, nome_cidade=nome_cidade.upper())

def get_or_create_bairro(empresa, nome_bairro):
    if not nome_bairro:
        return None
    bairro = Bairro.objects.filter(vinc_emp=empresa, nome_bairro__iexact=nome_bairro).first()
    if bairro:
        return bairro
    return Bairro.objects.create(vinc_emp=empresa, nome_bairro=nome_bairro.upper())

@login_required
@require_POST
@transaction.atomic
def criar_fornecedor_por_xml(request):
    empresa = request.user.empresa
    arquivo = request.FILES.get("xml")
    if not arquivo:
        return JsonResponse({"ok": False, "erro": "XML não enviado."}, status=400)
    try:
        tree = ET.parse(arquivo)
        root = tree.getroot()
        ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
        emit = root.find(".//nfe:emit", ns)
        ender = emit.find("nfe:enderEmit", ns) if emit is not None else None
        cpf_cnpj = somente_numeros(get_text(emit, "nfe:CNPJ", ns) or get_text(emit, "nfe:CPF", ns))
        ie = get_text(emit, "nfe:IE", ns)
        razao_social = get_text(emit, "nfe:xNome", ns)
        fantasia = get_text(emit, "nfe:xFant", ns) or razao_social
        endereco = get_text(ender, "nfe:xLgr", ns)
        numero = get_text(ender, "nfe:nro", ns) or "S/N"
        bairro_nome = get_text(ender, "nfe:xBairro", ns)
        cidade_nome = get_text(ender, "nfe:xMun", ns)
        estado_nome = get_text(ender, "nfe:UF", ns)
        cep = somente_numeros(get_text(ender, "nfe:CEP", ns))
        tel = somente_numeros(get_text(ender, "nfe:fone", ns))
        if not cpf_cnpj or not razao_social:
            return JsonResponse({"ok": False, "erro": "XML sem CNPJ/CPF ou razão social do fornecedor."}, status=400)
        fornecedor = Fornecedor.objects.filter(vinc_emp=empresa, cpf_cnpj=cpf_cnpj).first()
        if fornecedor:
            return JsonResponse({"ok": True, "fornecedor": {"id": fornecedor.id, "nome": fornecedor.razao_social or fornecedor.fantasia, "ja_existia": True}})
        estado = get_or_create_estado(empresa, estado_nome)
        cidade = get_or_create_cidade(empresa, cidade_nome)
        bairro = get_or_create_bairro(empresa, bairro_nome)
        fornecedor = Fornecedor.objects.create(vinc_emp=empresa, situacao="Ativo", pessoa="Jurídica" if len(cpf_cnpj) == 14 else "Física", cpf_cnpj=cpf_cnpj, ie=ie or None, razao_social=razao_social, fantasia=fantasia,
            endereco=endereco or "NÃO INFORMADO", cep=cep or "00000000", numero=numero, bairro=bairro, cidade=cidade, uf=estado, complem="", tel=tel or "00000000000", email="sememail@fornecedor.local", dt_reg=date.today()
        )
        return JsonResponse({"ok": True, "fornecedor": {"id": fornecedor.id, "nome": fornecedor.razao_social or fornecedor.fantasia, "ja_existia": False}})

    except Exception as e:
        return JsonResponse({"ok": False, "erro": f"Erro ao criar fornecedor: {str(e)}"}, status=400)

@login_required
@require_POST
@transaction.atomic
def criar_produto_por_xml(request):
    empresa = request.user.empresa
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "erro": "JSON inválido."}, status=400)
    fornecedor_id = body.get("fornecedor_id")
    produto_existente_id = body.get("produto_existente_id")
    grupo_id = body.get("grupo_id")
    marca_id = body.get("marca_id")
    unidade_id = body.get("unidade_id")
    tp_prod = (body.get("tp_prod") or "Principal").strip()
    descricao = (body.get("descricao", "") or "").strip()
    unidade = (body.get("unidade", "") or "").strip()
    ean = (body.get("ean", "") or "").strip()
    codigo_fornecedor = (body.get("codigo_fornecedor", "") or "").strip()
    descricao_fornecedor = (body.get("descricao_fornecedor", "") or descricao).strip()
    fornecedor = None
    if fornecedor_id:
        fornecedor = Fornecedor.objects.filter(id=fornecedor_id, vinc_emp=empresa).first()
    grupo = None
    if grupo_id:
        grupo = Grupo.objects.filter(id=grupo_id, vinc_emp=empresa).first()
    marca = None
    if marca_id:
        marca = Marca.objects.filter(id=marca_id, vinc_emp=empresa).first()
    unidade = None
    if unidade_id:
        unidade = Unidade.objects.filter(id=unidade_id, vinc_emp=empresa).first()
    if not descricao and not produto_existente_id:
        return JsonResponse({"ok": False, "erro": "Descrição do produto obrigatória."}, status=400)
    if produto_existente_id:
        try:
            produto = Produto.objects.get(id=produto_existente_id, vinc_emp=empresa)
        except Produto.DoesNotExist:
            return JsonResponse({"ok": False, "erro": "Produto selecionado não encontrado."}, status=404)
        if ean and ean not in ["SEM GTIN", "SEMGTIN"]:
            CodigoProduto.objects.get_or_create(vinc_emp=empresa, codigo=ean, defaults={"produto": produto})
        if fornecedor and codigo_fornecedor:
            ProdutoFornecedor.objects.update_or_create(vinc_emp=empresa, fornecedor=fornecedor, codigo_fornecedor=codigo_fornecedor, defaults={"produto": produto, "descricao_fornecedor": descricao_fornecedor})
        return JsonResponse({"ok": True, "produto": {"id": produto.id, "descricao": produto.desc_prod, "ja_existia": True,} })
    produto = None
    if ean and ean not in ["SEM GTIN", "SEMGTIN"]:
        codigo_obj = CodigoProduto.objects.filter(vinc_emp=empresa, codigo=ean).select_related("produto").first()
        if codigo_obj:
            produto = codigo_obj.produto
    if not produto:
        produto = Produto.objects.create(vinc_emp=empresa, desc_prod=descricao, grupo=grupo, unidProd=unidade, marca=marca, tp_prod=tp_prod if tp_prod in ["Principal", "Adicional"] else "Principal",
            situacao="Ativo", vl_compra=Decimal("0.00"), estoque_prod=Decimal("0.00"))
        ja_existia = False
    else:
        ja_existia = True
    if ean and ean not in ["SEM GTIN", "SEMGTIN"]:
        CodigoProduto.objects.get_or_create(vinc_emp=empresa, codigo=ean, defaults={"produto": produto})
    if fornecedor and codigo_fornecedor:
        ProdutoFornecedor.objects.update_or_create(vinc_emp=empresa, fornecedor=fornecedor, codigo_fornecedor=codigo_fornecedor,
            defaults={"produto": produto, "descricao_fornecedor": descricao_fornecedor}
        )
    return JsonResponse({"ok": True, "produto": {"id": produto.id, "descricao": produto.desc_prod, "ja_existia": ja_existia,}})

def montar_produtos_post(post_data):
    produtos_dict = {}
    for key, value in post_data.items():
        m_prod = re.match(r"^produtos\[(\d+)\]\[(codigo|produto|quantidade|preco_unitario|desconto)\]$", key)
        m_tab = re.match(r"^produtos\[(\d+)\]\[tabelas\]\[(\d+)\]\[(tabela_id|tabela_nome|margem|valor)\]$", key)
        if m_prod:
            idx, campo = m_prod.groups()
            if idx not in produtos_dict:
                produtos_dict[idx] = {"tabelas": {}}
            produtos_dict[idx][campo] = value
        elif m_tab:
            idx, tab_idx, campo = m_tab.groups()
            if idx not in produtos_dict:
                produtos_dict[idx] = {"tabelas": {}}
            if tab_idx not in produtos_dict[idx]["tabelas"]:
                produtos_dict[idx]["tabelas"][tab_idx] = {}
            produtos_dict[idx]["tabelas"][tab_idx][campo] = value
    return produtos_dict

@verifica_alguma_permissao('entradas.add_entrada', 'entradas.change_entrada', 'entradas.delete_entrada')
@login_required
@transaction.atomic
def add_entrada(request):
    error_messages = []
    if not request.user.has_perm('entradas.add_entrada'):
        messages.info(request, 'Você não tem permissão para adicionar entradas de NF/Pedidos.')
        return redirect('/entradas/lista/')
    try:
        if request.method == "POST":
            form = EntradaForm(request.POST, empresa=request.user.empresa, user=request.user)
            if not form.is_valid():
                error_messages = [f"Campo ({field.label}) é obrigatório!" for field in form if field.errors]
                return render(request, 'entradas/add.html', {'form': form, 'error_messages': error_messages})
            entrada = form.save(commit=False)
            if entrada.fornecedor and entrada.fornecedor.vinc_emp != request.user.empresa:
                return HttpResponseForbidden()
            if entrada.vinc_fil and entrada.vinc_fil.vinc_emp != request.user.empresa:
                return HttpResponseForbidden()
            entrada.vinc_emp = request.user.empresa
            entrada.save()
            produtos_dict = montar_produtos_post(request.POST)
            for dados in produtos_dict.values():
                try:
                    produto = Produto.objects.get(pk=dados.get("codigo"), vinc_emp=request.user.empresa)
                except Produto.DoesNotExist:
                    messages.warning(request, f"Produto {dados.get('produto')} não encontrado e foi ignorado.")
                    continue
                ep = EntradaProduto.objects.create(
                    entrada=entrada,
                    produto=produto,
                    quantidade=parse_decimal(dados.get("quantidade")),
                    preco_unitario=parse_decimal(dados.get("preco_unitario")),
                    desconto=parse_decimal(dados.get("desconto"))
                )
                for tab in dados.get("tabelas", {}).values():
                    tabela_id = tab.get("tabela_id")
                    if not tabela_id:
                        continue
                    try:
                        tabela = TabelaPreco.objects.get(pk=tabela_id, vinc_emp=request.user.empresa)
                    except TabelaPreco.DoesNotExist:
                        messages.warning(request, f"Tabela {tabela_id} não encontrada para o produto {dados.get('produto')}.")
                        continue
                    try:
                        valor = parse_decimal(tab.get("valor"))
                    except Exception:
                        valor = Decimal('0.00')
                    try:
                        margem = parse_decimal(tab.get("margem"))
                    except Exception:
                        margem = Decimal('0.00')
                    EntradaProdutoTabela.objects.create(
                        entrada_produto=ep,
                        tabela_preco=tabela,
                        margem=margem,
                        valor=valor
                    )
                    ProdutoTabela.objects.update_or_create(
                        produto=produto,
                        tabela=tabela,
                        defaults={
                            "vl_prod": valor,
                            "margem": margem
                        }
                    )
            entrada.total = entrada.atualizar_total()
            entrada.save(update_fields=["total"])
            messages.success(request, f'Registro de {entrada.tipo} - {entrada.numeracao} realizado com sucesso!')
            return redirect(f'/entradas/lista/?tp=numeracao&s={entrada.numeracao}')
        form = EntradaForm(empresa=request.user.empresa, user=request.user)
    except ObjectDoesNotExist:
        error_messages.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {str(e)}")
    except DatabaseError as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco de dados: {str(e)}")
    except Exception as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return render(request, "entradas/add.html", {"form": form, "error_messages": error_messages})

@login_required
@transaction.atomic
def att_entrada(request, id):
    error_messages = []
    entrada = get_object_or_404(Entrada, pk=id, vinc_emp=request.user.empresa)
    if not request.user.has_perm('entradas.change_entrada'):
        messages.info(request, 'Você não tem permissão para editar entradas de NF/Pedidos.')
        return redirect('/entradas/lista/')
    if entrada.situacao == "Efetivada" and entrada.tipo == "Nota Fiscal":
        messages.warning(request, f'{entrada.tipo} - {entrada.numeracao} já efetivada, impossível alterar!')
        return redirect(f'/entradas/lista/?tp=numeracao&s={entrada.numeracao}')
    if entrada.situacao == "Efetivada" and entrada.tipo == "Pedido":
        messages.warning(request, f'{entrada.tipo} - {entrada.numeracao} já efetivado, impossível alterar!')
        return redirect(f'/entradas/lista/?tp=numeracao&s={entrada.numeracao}')
    try:
        if request.method == "POST":
            form = EntradaForm(request.POST, instance=entrada, empresa=request.user.empresa, user=request.user)
            if not form.is_valid():
                error_messages = [f"Campo ({field.label}) é obrigatório!" for field in form if field.errors]
                return render(request, "entradas/att.html", {"form": form, "entrada": entrada, "error_messages": error_messages})
            entrada = form.save(commit=False)
            if entrada.fornecedor and entrada.fornecedor.vinc_emp != request.user.empresa:
                return HttpResponseForbidden()
            if entrada.vinc_fil and entrada.vinc_fil.vinc_emp != request.user.empresa:
                return HttpResponseForbidden()
            entrada.vinc_emp = request.user.empresa
            entrada.save()
            next_url = request.POST.get('next') or request.GET.get('next')
            produtos_dict = montar_produtos_post(request.POST)
            itens_ids_mantidos = []
            for dados in produtos_dict.values():
                try:
                    produto = Produto.objects.get(pk=dados.get("codigo"), vinc_emp=request.user.empresa)
                except Produto.DoesNotExist:
                    messages.warning(request, f"Produto {dados.get('produto')} não encontrado e foi ignorado.")
                    continue
                ep, created = EntradaProduto.objects.update_or_create(
                    entrada=entrada,
                    produto=produto,
                    defaults={
                        "quantidade": parse_decimal(dados.get("quantidade")),
                        "preco_unitario": parse_decimal(dados.get("preco_unitario")),
                        "desconto": parse_decimal(dados.get("desconto"))
                    }
                )
                itens_ids_mantidos.append(ep.id)
                tab_ids_mantidas = []
                for tab in dados.get("tabelas", {}).values():
                    tabela_id = tab.get("tabela_id")
                    if not tabela_id:
                        continue
                    try:
                        tabela = TabelaPreco.objects.get(pk=tabela_id, vinc_emp=request.user.empresa)
                    except TabelaPreco.DoesNotExist:
                        messages.warning(request, f"Tabela {tabela_id} não encontrada para o produto {dados.get('produto')}.")
                        continue
                    try:
                        valor = parse_decimal(tab.get("valor"))
                    except Exception:
                        valor = Decimal('0.00')
                    try:
                        margem = parse_decimal(tab.get("margem"))
                    except Exception:
                        margem = Decimal('0.00')
                    ept, created = EntradaProdutoTabela.objects.update_or_create(
                        entrada_produto=ep,
                        tabela_preco=tabela,
                        defaults={
                            "margem": margem,
                            "valor": valor
                        }
                    )
                    tab_ids_mantidas.append(ept.id)
                    ProdutoTabela.objects.update_or_create(
                        produto=produto,
                        tabela=tabela,
                        defaults={
                            "vl_prod": valor,
                            "margem": margem
                        }
                    )
                EntradaProdutoTabela.objects.filter(
                    entrada_produto=ep,
                    tabela_preco__vinc_emp=request.user.empresa
                ).exclude(id__in=tab_ids_mantidas).delete()
            EntradaProdutoTabela.objects.filter(
                entrada_produto__entrada=entrada,
                entrada_produto__produto__vinc_emp=request.user.empresa
            ).exclude(entrada_produto_id__in=itens_ids_mantidos).delete()
            EntradaProduto.objects.filter(
                entrada=entrada,
                produto__vinc_emp=request.user.empresa
            ).exclude(id__in=itens_ids_mantidos).delete()
            entrada.total = entrada.atualizar_total()
            entrada.save(update_fields=["total"])
            messages.success(request, f'Registro de {entrada.tipo} - {entrada.numeracao} atualizado com sucesso!')
            if next_url:
                return redirect(next_url)
            else:
                return redirect(f'/entradas/lista/?tp=numeracao&s={entrada.numeracao}')
        form = EntradaForm(instance=entrada, empresa=request.user.empresa, user=request.user)
    except ObjectDoesNotExist:
        error_messages.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {str(e)}")
    except DatabaseError as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco de dados: {str(e)}")
    except Exception as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return render(request, "entradas/att.html", {"form": form, "entrada": entrada, "produtos": entrada.itens.all(), "error_messages": error_messages})

@login_required
def del_entrada(request, id):
    entrada = get_object_or_404(Entrada, pk=id, vinc_emp=request.user.empresa)
    if not request.user.has_perm('entradas.delete_entrada'):
        messages.info(request, 'Você não tem permissão para deletar entradas de NF/Pedidos.')
        return redirect('/entradas/lista/')
    if entrada.situacao == "Efetivada" and entrada.tipo == "Nota Fiscal":
        messages.warning(request, f'{entrada.tipo} - {entrada.numeracao} já efetivada, impossível deletar!')
        return redirect(f'/entradas/lista/?tp=numeracao&s={entrada.numeracao}')
    elif entrada.situacao == "Efetivada" and entrada.tipo == "Pedido":
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
    entrada = get_object_or_404(Entrada, pk=id, vinc_emp=request.user.empresa)
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
            messages.success(request, f'Registro de {entrada.tipo} - {entrada.numeracao} efetivado com sucesso!')
        else:
            messages.warning(request, f'Entrada {entrada.numeracao} já foi efetivada antes.')
        return redirect(f'/entradas/lista/?tp=numeracao&s={entrada.numeracao}')

@require_POST
@login_required
def cancelar_entrada(request, id):
    entrada = get_object_or_404(Entrada, pk=id, vinc_emp=request.user.empresa)
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
                produto.estoque_prod = (produto.estoque_prod or 0) - (item.quantidade or 0)
                # Atualiza preço de compra
                produto.vl_compra = str(item.preco_unitario)  # já que vl_compra é CharField
                produto.save(update_fields=["estoque_prod", "vl_compra"])
            messages.success(request, f'Registro de {entrada.tipo} - {entrada.numeracao} cancelado com sucesso!')
        else:
            messages.warning(request, f'Entrada {entrada.numeracao} já foi cancelada antes.')
        return redirect(f'/entradas/lista/?tp=numeracao&s={entrada.numeracao}')