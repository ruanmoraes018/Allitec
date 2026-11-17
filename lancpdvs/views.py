import json
import os
from datetime import datetime, time
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from clientes.models import Cliente
from core.pagamentos.services import PagamentoService
from lancpdvs.models import Caixa, CaixaMovimento, CaixaFechamento
from lancpdvs.forms import CaixaForm
import unicodedata
from django.http import JsonResponse
from pedidos.models import Pagamento, Pedido, PedidoDevolucaoItem, PedidoProduto
from util.parse_decimal import parse_decimal
from util.permissoes import verifica_permissao
from django.db.models import Q
from filiais.models import Filial, Usuario
from formas_pgto.models import FormaPgto
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, DatabaseError, transaction
from lancpdvs.services import processar_itens_caixa, processar_estoque_caixa, processar_pagamentos_caixa, criar_devolucao_caixa, criar_credito_cliente, criar_contas_receber_caixa
import re
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from io import BytesIO
from django.conf import settings
import base64
from PIL import Image
from vendedores.models import Vendedor
from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum
from collections import defaultdict
from util.logs import gerar_alteracoes, registrar_log
from util.filiais import aplicar_filtro_filial
from tabelas_preco.models import TabelaPreco

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('lancpdvs.view_caixa')
@login_required
def lista_lancamentos(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    sit = request.GET.get('sit')
    fil = request.GET.get('fil')
    user1 = request.GET.get('user1')
    dt_ini = request.GET.get('dt_ini')
    dt_fim = request.GET.get('dt_fim')
    por_dt = request.GET.get('p_dt')
    hoje = datetime.today()
    inicio_dia = datetime.combine(hoje, time.min)
    fim_dia = datetime.combine(hoje, time.max)
    reg = request.GET.get('reg', '10')
    empresa = request.user.empresa
    caixas = Caixa.objects.filter(vinc_emp=empresa)
    # Aplica a regra de acesso às filiais
    caixas, aguardando_filial = aplicar_filtro_filial(request, caixas)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        caixas = caixas.filter(terminal__nome__icontains=norm_s).order_by('terminal__nome')
    elif tp == 'cod' and s:
        try: caixas = caixas.filter(codigo__iexact=s).order_by('terminal__nome')
        except ValueError: caixas = Caixa.objects.none()
    if por_dt == 'Sim' and dt_ini and dt_fim:
        try:
            dt_ini_dt = datetime.combine(datetime.strptime(dt_ini, '%d/%m/%Y').date(), time.min)
            dt_fim_dt = datetime.combine(datetime.strptime(dt_fim, '%d/%m/%Y').date(), time.max)
            caixas = caixas.filter(data_abertura__range=(dt_ini_dt, dt_fim_dt))
        except ValueError: caixas = Caixa.objects.none()
    filtros_ativos = any([s, tp, sit, por_dt == 'Sim', fil and user1])
    if not filtros_ativos and not aguardando_filial: caixas = caixas.filter(data_abertura__range=(inicio_dia, fim_dia), situacao='Aberto')
    if sit and sit != 'Todos': caixas = caixas.filter(situacao=sit)
    if fil: caixas = caixas.filter(vinc_fil__codigo=fil)
    if user1: caixas = caixas.filter(usuario__codigo_local=user1)
    filiais = Filial.objects.filter(vinc_emp=request.user.empresa)
    usuarios = Usuario.objects.filter(empresa=request.user.empresa)
    if reg == 'todos': num_pagina = caixas.count() or 1
    else:
        try: num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError: num_pagina = 10  # Valor padrão
    paginator = Paginator(caixas, num_pagina)
    page = request.GET.get('page')
    caixas = paginator.get_page(page)
    cx_ab_pg = sum(1 for p in caixas.object_list if p.situacao == 'Aberto')
    cx_fec_pg = sum(1 for p in caixas.object_list if p.situacao == 'Fechado')
    return render(request,'lancpdvs/lista.html',{'caixas':caixas,'filiais':filiais,'usuarios':usuarios,'user1': user1,'fil':fil,'dt_ini':dt_ini,'dt_fim':dt_fim,'sit':sit,'p_dt':por_dt,
        's':s,'tp':tp,'reg':reg,'cx_ab':cx_ab_pg,'cx_fec':cx_fec_pg
    })

@login_required
def lista_lancamentos_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit(): condicao_busca = Q(nome__icontains=termo_busca) | Q(codigo=termo_busca)
        else: condicao_busca = Q(nome__icontains=termo_busca)
        caixas = Caixa.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': p.codigo, 'text': f"{p.terminal.nome.upper()}"} for p in caixas]
        return JsonResponse({'results': results})
    except Exception as e:
        return JsonResponse({'results': [], 'error': str(e)})

@login_required
def add_lancamento(request):
    error_messages = []
    empresa = request.user.empresa
    if not request.user.has_perm('lancpdvs.add_caixa'):
        messages.info(request, 'Você não tem permissão para adicionar caixas.')
        return redirect('/lancpdvs/lista/')
    if request.method != 'POST':
        form = CaixaForm(empresa=empresa)
        formas = FormaPgto.objects.filter(vinc_emp=empresa, tipo='A vista', situacao='Ativo').values('codigo', 'descricao')
        return render(request, 'lancpdvs/add.html', {'form': form, 'formas_json': list(formas), 'error_messages': error_messages})
    data = request.POST.copy()
    for key in data:
        if key.startswith('forma_'):
            v = data.get(key)
            if not v or v.strip() == '': data[key] = Decimal('0')
            else:
                v = re.sub(r'[^\d,.-]', '', v)
                v = v.replace('.', '').replace(',', '.')
                try: data[key] = Decimal(v)
                except: data[key] = Decimal('0')
    form = CaixaForm(data, empresa=request.user.empresa)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'lancpdvs/add.html', {'form': form, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            caixa = form.save(commit=False)
            caixa.vinc_emp = request.user.empresa
            caixa.vinc_fil = caixa.terminal.vinc_fil
            caixa.usuario = request.user
            caixa.situacao = 'Aberto'
            caixa.save()
            registrar_log(request,"ABERTURA","Caixa",caixa.terminal.nome,f"Realizou a abertura do caixa: {caixa.codigo} - {caixa.terminal.nome}",caixa.id,gerar_alteracoes(obj_novo=caixa))
            formas = FormaPgto.objects.filter(vinc_emp=empresa)
            for forma in formas:
                valor = form.cleaned_data.get(f'forma_{forma.codigo}') or Decimal('0')
                if valor > 0: CaixaMovimento.objects.create(caixa=caixa, tipo='Entrada', categoria='Saldo Inicial', forma_pagamento=forma, valor=valor, usuario=request.user)
            messages.success(request, 'Caixa aberto com sucesso!')
            return redirect(f'/lancpdvs/lista/?tp=cod&s={caixa.codigo}')
    except ObjectDoesNotExist: error_messages.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        detalhe = str(e.__cause__ if e.__cause__ else e)
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {detalhe}")
    except DatabaseError as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except ValueError as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> {str(e)}")
    except Exception as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    formas = FormaPgto.objects.filter(vinc_emp=empresa, tipo='A vista', situacao='Ativo').values('codigo', 'descricao')
    return render(request, 'lancpdvs/add.html', {'form': form, 'formas_json': list(formas), 'error_messages': error_messages})

@login_required
def att_lancamento(request, codigo):
    error_messages = []
    empresa = request.user.empresa
    b = get_object_or_404(Caixa, codigo=codigo, vinc_emp=empresa)
    it_old = Caixa.objects.get(codigo=b.codigo, vinc_emp=empresa)
    if not request.user.has_perm('lancpdvs.change_caixa'):
        messages.info(request, 'Você não tem permissão para editar caixas.')
        return redirect('/lancpdvs/lista/')
    if request.method != 'POST':
        form = CaixaForm(instance=b, empresa=empresa)
        formas = FormaPgto.objects.filter(vinc_emp=empresa, situacao='Ativo').values('codigo', 'descricao')
        return render(request, 'lancpdvs/att.html', {'form': form, 'b': b, 'formas_json': list(formas), 'error_messages': error_messages})
    form = CaixaForm(request.POST, instance=b, empresa=empresa)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'lancpdvs/att.html', {'form': form, 'b': b, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            b.save()
            registrar_log(request, "ALTERAR", "Caixa", b.terminal.nome, f"Alterou o caixa: {b.codigo} - {b.terminal.nome}", b.id, gerar_alteracoes(it_old, b))
            next_url = request.POST.get('next') or request.GET.get('next')
            bank = str(b.codigo)
            messages.success(request, 'Caixa atualizado com sucesso!')
            if next_url: return redirect(next_url)
            else: return redirect('/lancpdvs/lista/?tp=cod&s=' + bank)
    except ObjectDoesNotExist:
        error_messages.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        detalhe = str(e.__cause__ if e.__cause__ else e)
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {detalhe}")
    except DatabaseError as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except ValueError as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> {str(e)}")
    except Exception as e:
        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    formas = FormaPgto.objects.filter(vinc_emp=empresa, situacao='Ativo').values('codigo', 'descricao')
    return render(request, 'lancpdvs/att.html', {'form': form, 'b': b, 'formas_json': list(formas), 'error_messages': error_messages})

@login_required
def del_lancamento(request, codigo):
    if not request.user.has_perm('lancpdvs.delete_caixa'):
        messages.info(request, 'Você não tem permissão para deletar caixas.')
        return redirect('/lancpdvs/lista/')
    try:
        with transaction.atomic():
            b = get_object_or_404(Caixa, codigo=codigo, vinc_emp=request.user.empresa)
            if b.caixamovimento_set.exists():
                messages.error(request, 'Não é possível deletar este caixa porque existem movimentos associados a ele.')
                return redirect('/lancpdvs/lista/')
            else:
                registrar_log(request, "EXCLUIR", "Caixa", b.terminal.caixa, f"Excluiu o caixa: {b.codigo} - {b.terminal.caixa}", b.id, gerar_alteracoes(obj_antigo=b))
                b.delete()
                messages.success(request, 'Caixa deletado com sucesso!')
                return redirect('/lancpdvs/lista/')
    except ObjectDoesNotExist:
        messages.error(request, "<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        detalhe = str(e.__cause__ if e.__cause__ else e)
        messages.error(request, f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {detalhe}")
    except DatabaseError as e:
        messages.error(request, f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except ValueError as e:
        messages.error(request, f"<i class='fa-solid fa-xmark'></i> {str(e)}")
    except Exception as e:
        messages.error(request, f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return redirect('/lancpdvs/lista/')

@login_required
def tela_caixa(request, caixa_id):
    empresa = request.user.empresa
    caixa = get_object_or_404(Caixa, codigo=caixa_id, vinc_emp=empresa, situacao='Aberto')
    if (not request.user.has_perm('lancpdvs.caixa_outro_user') and caixa.usuario != request.user):
        messages.error(request, 'Seu usuário não pode realizar lançamentos em caixas de outros usuários!')
        return redirect('lista-lancamentos')
    formas = FormaPgto.objects.filter(vinc_emp=empresa, situacao='Ativo')
    logo_base64 = None
    logo_path = os.path.join(settings.MEDIA_ROOT, str(caixa.vinc_fil.logo))
    if caixa.vinc_fil.logo and os.path.exists(logo_path):
        with Image.open(logo_path) as img:
            if img.mode in ('RGBA', 'LA'):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            else: img = img.convert("RGB")
            buffer = BytesIO()
            img.save(buffer, format="JPEG")
            logo_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    vendedores = Vendedor.objects.filter(vinc_emp=empresa, situacao='Ativo')
    return render(request, 'lancpdvs/caixa.html', {'caixa': caixa, 'formas_pgto': formas, 'vendedores': vendedores, 'logo_base64': logo_base64})

@login_required
def realizar_entrada_caixa(request, caixa_id):
    erros = []
    empresa = request.user.empresa
    if request.method != "POST":
        return JsonResponse({"sucesso": False}, status=400)
    try:
        with transaction.atomic():
            caixa = Caixa.objects.get(codigo=caixa_id, vinc_emp=empresa, situacao='Aberto')
            forma = FormaPgto.objects.get(codigo=request.POST.get('forma_pagamento_entrada'), vinc_emp=empresa)
            m=CaixaMovimento.objects.create(caixa=caixa,tipo='Entrada',categoria='Suprimento',forma_pagamento=forma,valor=parse_decimal(request.POST.get('valor')),
                descricao=request.POST.get('descricao'),usuario=request.user
            )
            return JsonResponse({
                "sucesso":True,"fantasia":m.caixa.vinc_fil.fantasia,"endereco":m.caixa.vinc_fil.endereco,"numero":m.caixa.vinc_fil.numero,
                "bairro":m.caixa.vinc_fil.bairro_fil.nome_bairro,"cidade":m.caixa.vinc_fil.cidade_fil.nome_cidade,"uf": m.caixa.vinc_fil.uf.nome_estado,"tel":m.caixa.vinc_fil.tel,
                "caixa": m.caixa.terminal.nome,"cod_cx":m.caixa.codigo,"id": m.codigo,"tipo":m.tipo,"categoria":m.categoria,"forma":forma.descricao,"valor":float(m.valor),
                "descricao":m.descricao,"usuario":request.user.first_name,"data":timezone.localtime(m.data_hora).strftime("%d/%m/%Y %H:%M:%S")
            })
    except ObjectDoesNotExist:
        erros.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        detalhe = str(e.__cause__ if e.__cause__ else e)
        erros.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {detalhe}")
    except DatabaseError as e:
        erros.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except ValueError as e:
        erros.append(f"<i class='fa-solid fa-xmark'></i> {str(e)}")
    except Exception as e:
        erros.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return JsonResponse({"sucesso": False, "erro": erros}, status=500)

@login_required
def realizar_saida_caixa(request, caixa_id):
    if request.method != "POST":
        return JsonResponse({"sucesso": False}, status=400)
    erros = []
    empresa = request.user.empresa
    try:
        with transaction.atomic():
            caixa = Caixa.objects.get(codigo=caixa_id, vinc_emp=empresa, situacao='Aberto')
            forma = FormaPgto.objects.get(codigo=request.POST.get('forma_pagamento_saida'), vinc_emp=empresa)
            m = CaixaMovimento.objects.create(caixa=caixa, tipo='Saída', categoria='Sangria', forma_pagamento=forma, valor=parse_decimal(request.POST.get('valor')),
                descricao=request.POST.get('descricao'), usuario=request.user
            )
            return JsonResponse({
                "sucesso":True,"fantasia":m.caixa.vinc_fil.fantasia,"endereco":m.caixa.vinc_fil.endereco,"numero":m.caixa.vinc_fil.numero,
                "bairro":m.caixa.vinc_fil.bairro_fil.nome_bairro,"cidade":m.caixa.vinc_fil.cidade_fil.nome_cidade,"uf":m.caixa.vinc_fil.uf.nome_estado,"tel":m.caixa.vinc_fil.tel,
                "caixa":m.caixa.terminal.nome,"cod_cx":m.caixa.codigo,"id":m.codigo,"tipo":m.tipo,"categoria":m.categoria,"forma":forma.descricao,"valor":float(m.valor),
                "descricao":m.descricao,"usuario":request.user.first_name,"data":timezone.localtime(m.data_hora).strftime("%d/%m/%Y %H:%M:%S")
            })
    except ObjectDoesNotExist:
        erros.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        detalhe = str(e.__cause__ if e.__cause__ else e)
        erros.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {detalhe}")
    except DatabaseError as e:
        erros.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except ValueError as e:
        erros.append(f"<i class='fa-solid fa-xmark'></i> {str(e)}")
    except Exception as e:
        erros.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return JsonResponse({"sucesso": False, "erro": erros}, status=500)

@login_required
@require_POST
def cancelar_movimento_caixa(request, caixa_id, movimento_id):
    erros = []
    empresa = request.user.empresa
    try:
        with transaction.atomic():
            movimento = get_object_or_404(CaixaMovimento.objects.select_related("caixa"), caixa__codigo=caixa_id, caixa__vinc_emp=empresa, codigo=movimento_id)
            if movimento.caixa.situacao == "Fechado":
                erros.append("O caixa já está fechado.")
                return JsonResponse({"erro": erros}, status=400)
            if movimento.situacao == "Cancelado":
                erros.append("Este lançamento já foi cancelado.")
                return JsonResponse({"erro": erros}, status=400)
            if movimento.categoria == "Venda":
                erros.append("Movimentos de venda não podem ser cancelados por esta tela.")
                return JsonResponse({"erro": erros}, status=400)
            movimento.situacao = "Cancelado"
            movimento.save(update_fields=["situacao"])
            tipo = movimento.tipo
            return JsonResponse({"sucesso": True, "mensagem": f"{tipo} cancelada com sucesso!"})
    except ObjectDoesNotExist:
        erros.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        detalhe = str(e.__cause__ if e.__cause__ else e)
        erros.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {detalhe}")
    except DatabaseError as e:
        erros.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except ValueError as e:
        erros.append(f"<i class='fa-solid fa-xmark'></i> {str(e)}")
    except Exception as e:
        erros.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return JsonResponse({"erro": erros}, status=500)

@login_required
def dados_movimento_caixa(request, caixa_codigo, movimento_codigo):
    erros = []
    empresa = request.user.empresa
    try:
        m=(CaixaMovimento.objects.select_related("caixa","forma_pagamento","usuario","caixa__vinc_emp").get(caixa__codigo=caixa_codigo,caixa__vinc_emp=empresa,
            codigo=movimento_codigo
        ))
        filial = m.caixa.vinc_fil
        return JsonResponse({"sucesso":True,"tipo":m.tipo,"id":m.codigo,"cod_cx":m.caixa.codigo,"caixa":m.caixa.terminal.nome,"descricao":m.descricao,
            "forma":m.forma_pagamento.descricao,"valor":float(m.valor),"data":timezone.localtime(m.data_hora).strftime("%d/%m/%Y %H:%M:%S"),"fantasia":filial.fantasia,
            "endereco":filial.endereco,"numero":filial.numero,"bairro":filial.bairro_fil.nome_bairro,"cidade":filial.cidade_fil.nome_cidade,"uf":filial.uf.nome_estado,"tel":filial.tel,
        })
    except CaixaMovimento.DoesNotExist:
        erros.append("Movimento não encontrado.")
        return JsonResponse({"sucesso": False, "erro": erros}, status=404)
    return JsonResponse({"sucesso": False, "erro": erros}, status=500)

@login_required
def movimentos_caixa(request, caixa_id):
    empresa = request.user.empresa
    try:
        caixa = Caixa.objects.get(codigo=caixa_id, vinc_emp=empresa)
        movs = caixa.movimentos.select_related('forma_pagamento', 'pedido', 'pedido__cli', 'pedido__vendedor')
        # ABERTURA
        abertura_qs = movs.filter(categoria='Saldo Inicial')
        if not abertura_qs.exists():
            abertura = [{"data": caixa.data_abertura, "descricao": "Abertura do caixa", "forma": "-", "valor": float(caixa.saldo_inicial or 0)}]
        else:
            abertura = [{"data":m.data_hora,"descricao":m.descricao or "Abertura do caixa","forma":m.forma_pagamento.descricao if m.forma_pagamento else "-",
                "valor": float(m.valor)} for m in abertura_qs
            ]
        # VENDAS (EXIBIÇÃO)
        vendas_qs = movs.filter(categoria='Venda').order_by('pedido_id')
        vendas_dict = {}
        for m in vendas_qs:
            pedido_id = m.pedido.codigo
            if pedido_id not in vendas_dict:
                vendas_dict[pedido_id] = {"pedido_id":pedido_id,"cliente":f"{getattr(m.pedido.cli, 'codigo', '-') or '-'} - {getattr(m.pedido.cli, 'fantasia', '-')}",
                    "vendedor":f"{getattr(m.pedido.vendedor, 'codigo', '-') or '-'} - {getattr(m.pedido.vendedor, 'fantasia', '-')}","data":m.pedido.dt_emi,"situacao":m.pedido.situacao,
                    "formas":[],"total":0,"tem_devolucao":m.pedido.tipo_operacao in ('Troca', 'Devolucao'),
                }
            vendas_dict[pedido_id]["formas"].append({
                "forma": m.forma_pagamento.descricao if m.forma_pagamento else "-",
                "valor": float(m.valor), "situacao": m.situacao
            })
            # Apenas para exibição
            vendas_dict[pedido_id]["total"] += float(m.valor)
        vendas = list(vendas_dict.values())
        # VENDAS (TOTAIS)
        vendas_total_qs = movs.filter(categoria='Venda', situacao='Ativo', pedido__situacao='Faturado')
        resumo_temp = defaultdict(lambda: {"id": None, "forma": "", "total": 0})
        for m in vendas_total_qs:
            fp_id = m.forma_pagamento.codigo if m.forma_pagamento else 0
            resumo_temp[fp_id]["id"] = fp_id
            resumo_temp[fp_id]["forma"] = (m.forma_pagamento.descricao if m.forma_pagamento else "-")
            resumo_temp[fp_id]["total"] += float(m.valor)
        resumo_vendas = list(resumo_temp.values())
        total_vendas = float(vendas_total_qs.aggregate(total=Sum('valor'))['total'] or 0)
        # ENTRADAS (EXIBIÇÃO)
        entradas_qs = movs.filter(tipo='Entrada', categoria='Suprimento').order_by('forma_pagamento__codigo')
        entradas = [{"codigo": m.codigo, "descricao": m.descricao or "-",
            "forma": m.forma_pagamento.descricao if m.forma_pagamento else "-", "valor": float(m.valor), "situacao": m.situacao} for m in entradas_qs]
        # ENTRADAS (TOTAIS)
        entradas_total_qs = entradas_qs.filter(situacao='Ativo')
        resumo_entradas = [{"forma": r["forma_pagamento__descricao"], "total": float(r["total"])}
            for r in entradas_total_qs.values("forma_pagamento__descricao").annotate(total=Sum("valor"))]
        total_entradas = float(entradas_total_qs.aggregate(total=Sum("valor"))["total"] or 0)
        # SAÍDAS (EXIBIÇÃO)
        saidas_qs = movs.filter(tipo='Saída', categoria='Sangria').order_by('forma_pagamento__codigo')
        saidas = [{"codigo": s.codigo, "descricao": s.descricao or "-",
            "forma": s.forma_pagamento.descricao if s.forma_pagamento else "-", "valor": float(s.valor), "situacao": s.situacao} for s in saidas_qs]
        # SAÍDAS (TOTAIS)
        saidas_total_qs = saidas_qs.filter(situacao='Ativo')
        resumo_saidas = [{"forma": r["forma_pagamento__descricao"], "total": float(r["total"])}
            for r in saidas_total_qs.values("forma_pagamento__descricao").annotate(total=Sum("valor"))]
        total_saidas = float(saidas_total_qs.aggregate(total=Sum("valor"))["total"] or 0)
        # TOTAL GERAL
        totais = defaultdict(float)
        # Vendas faturadas
        for m in vendas_total_qs:
            forma = m.forma_pagamento.descricao if m.forma_pagamento else "-"
            totais[forma] += float(m.valor)
        # Suprimentos
        for m in entradas_total_qs:
            forma = m.forma_pagamento.descricao if m.forma_pagamento else "-"
            totais[forma] += float(m.valor)
        # Sangrias
        for m in saidas_total_qs:
            forma = m.forma_pagamento.descricao if m.forma_pagamento else "-"
            totais[forma] -= float(m.valor)
        total_geral = [{"forma": forma, "total": total} for forma, total in totais.items()]
        valor_total_geral = (float(caixa.saldo_inicial or 0) + sum(totais.values()))
        return JsonResponse({"caixa":caixa.codigo,"abertura":abertura,"vendas":vendas,"resumo_vendas":resumo_vendas,"total_vendas":total_vendas,"entradas":entradas,
            "resumo_entradas":resumo_entradas,"total_entradas":total_entradas,"saidas":saidas,"resumo_saidas":resumo_saidas,"total_saidas":total_saidas,"total_geral":total_geral,
            "valor_total_geral":valor_total_geral,
        })
    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)

@login_required
@require_GET
def limite_cliente_caixa(request, codigo):
    cliente = Cliente.objects.filter(codigo=codigo, vinc_emp=request.user.empresa).first()
    if not cliente:return JsonResponse({'sucesso': False, 'erro': 'Cliente não encontrado.'}, status=404)
    return JsonResponse({'sucesso': True,'limite_credito': float(cliente.limite_credito),'limite_disponivel': float(cliente.limite_disponivel),'somente_avista': cliente.somente_avista,
        'bloqueado': cliente.bloqueado,'motivo_bloqueio': cliente.motivo_bloqueio or '',
    })

@login_required
@require_POST
def finalizar_venda(request):
    erros = []
    empresa = request.user.empresa
    try:
        with transaction.atomic():
            # 1. DADOS RECEBIDOS DO FRONT
            data = json.loads(request.body)
            caixa_id = data.get('caixa_id')
            itens = data.get('itens', [])
            pagamentos_front = data.get('pagamentos', [])
            cliente_id = data.get('cliente_id')
            vendedor_id = data.get('vendedor_id')
            tabela_preco_id = data.get('tabela_preco_id')
            codigo_pedido_origem = data.get('codigo_pedido_origem')
            if not caixa_id: return JsonResponse({'erro': ['Caixa não informado']},status=400)
            if not itens: return JsonResponse({'erro': ['Venda/Troca sem itens']},status=400)
            # 2. BUSCA E BLOQUEIA O CAIXA
            caixa = (Caixa.objects.select_for_update().select_related('vinc_fil','usuario','terminal',).get(codigo=caixa_id,vinc_emp=empresa,))
            if caixa.situacao != 'Aberto': return JsonResponse({'erro': ['Caixa fechado']},status=400)
            # 3. CLIENTE / VENDEDOR / TABELA DE PREÇO
            cliente = None
            vendedor = None
            tabela_preco = None
            if cliente_id: cliente = (Cliente.objects.select_for_update().filter(codigo=cliente_id, vinc_emp=empresa).first())
            if vendedor_id: vendedor = (Vendedor.objects.filter(codigo=vendedor_id,vinc_emp=empresa,).first())
            if tabela_preco_id: tabela_preco = (TabelaPreco.objects.filter(codigo=tabela_preco_id,vinc_emp=empresa,).first())
            # 4. SEPARA VENDA E DEVOLUÇÃO
            itens_venda_front = [item for item in itens if not item.get('is_devolucao')]
            itens_devolucao_front = [item for item in itens if item.get('is_devolucao')]
            if itens_devolucao_front and not codigo_pedido_origem: return JsonResponse({'erro': ['Código do pedido de origem não informado para a devolução.']},status=400)
            # 5. DEFINE TIPO DA OPERAÇÃO
            tipo_operacao_global = 'Venda'
            if itens_devolucao_front: tipo_operacao_global = ('Troca' if itens_venda_front else 'Devolucao')
            # 6. BUSCA PEDIDO ORIGINAL DA DEVOLUÇÃO
            pedido_original = None
            if itens_devolucao_front and codigo_pedido_origem:
                pedido_original = (Pedido.objects.filter(codigo=codigo_pedido_origem,vinc_emp=empresa,).first())
                if not pedido_original: return JsonResponse({'erro': [f'Pedido de origem {codigo_pedido_origem} não encontrado nesta empresa.']},status=400)
            # 7. VALIDA FORMAS DE PAGAMENTO
            valor_a_prazo = Decimal('0.00')
            for pg in pagamentos_front:
                forma_id = pg.get('forma_id')
                if not forma_id: raise ValueError('Forma de pagamento não informada.')
                forma = FormaPgto.objects.filter(codigo=forma_id, vinc_emp=empresa).first()
                if not forma: raise ValueError(f'Forma de pagamento {forma_id} não encontrada.')
                fin = caixa.vinc_fil.financeiro
                if (forma.tipo or '').strip().upper() == 'A PRAZO':
                    try:
                        n_parc = int(pg.get('parcelas') or 1)
                        n_dias = int(pg.get('dias') or 0)
                        valor_a_prazo += Decimal(str(pg.get('valor', 0)))
                    except (TypeError, ValueError, InvalidOperation): raise ValueError(f'Dados inválidos para a forma de pagamento {forma_id}.')
                    if n_parc > fin.max_parcelas: return JsonResponse({'erro': [f'Máximo de {fin.max_parcelas} parcelas permitido na filial.']}, status=400)
                    if n_dias > fin.max_dias_intervalo: return JsonResponse({'erro': [f'Máximo de {fin.max_dias_intervalo} dias de intervalo permitido na filial.']}, status=400)
            if valor_a_prazo > 0:
                if not cliente: return JsonResponse({'erro': ['Informe um cliente para vender a prazo.']}, status=400)
                pode, motivo = cliente.pode_comprar_a_prazo(valor_a_prazo)
                if not pode: return JsonResponse({'erro': [motivo]}, status=400)
            # 8. CRIA O PEDIDO
            pedido = Pedido.objects.create(vinc_emp=empresa,vinc_fil=caixa.vinc_fil,caixa=caixa,cli=cliente,vendedor=vendedor,usuario=caixa.usuario,tabela_preco=tabela_preco,
                dt_emi=timezone.localtime(timezone.now()),dt_fat=timezone.localtime(timezone.now()),tipo_operacao=tipo_operacao_global,pedido_origem=pedido_original,situacao='Aberto',
            )
            # 9. PROCESSA OS ITENS
            resultado_itens = processar_itens_caixa(itens=itens,pedido=pedido,)
            total_venda = resultado_itens['total_venda']
            total_devolucao = resultado_itens['total_devolucao']
            itens_para_devolucao_modelo = (resultado_itens['itens_devolucao'])
            # 10. PROCESSA ESTOQUE
            estoque = getattr(getattr(caixa.vinc_fil, 'estoque', None),'estoque_padrao',None)
            if not estoque: raise ValueError(f'A filial {caixa.vinc_fil} não possui estoque padrão configurado.')
            pode_vender_sem_estoque = (request.user.has_perm('pedidos.vender_sem_estoque_ped'))
            processar_estoque_caixa(itens=itens,estoque=estoque,usuario=caixa.usuario,permitir_negativo=pode_vender_sem_estoque,)
            # 11. REGISTRA DEVOLUÇÃO / TROCA
            if (itens_para_devolucao_modelo and pedido_original):
                criar_devolucao_caixa(caixa=caixa,pedido=pedido,pedido_original=pedido_original,cliente=cliente,tipo=tipo_operacao_global,total=total_devolucao, itens=itens_para_devolucao_modelo,)
            # 12. PROCESSA PAGAMENTOS
            resultado_pagamentos = processar_pagamentos_caixa(pedido=pedido,caixa=caixa,pagamentos=pagamentos_front,)
            total_pago = resultado_pagamentos['total_pago']
            # CaixaMovimento não deve usar bulk_create, pois o save() gera o código sequencial do movimento.
            for movimento in resultado_pagamentos['movimentos']:
                movimento.save()
            criar_contas_receber_caixa(pedido=pedido, caixa=caixa, cliente=cliente, contas_prazo=resultado_pagamentos['contas_prazo'])
            pagamentos_gateway = (resultado_pagamentos.get('pagamentos_gateway',[]))
            pix_pendente = any(pagamento.status == 'pendente' for pagamento in pagamentos_gateway)
            # 13. GERA CRÉDITO DO CLIENTE
            if total_venda < 0: criar_credito_cliente(caixa=caixa,total_venda=total_venda,cliente=cliente,pedido=pedido,pedido_original=pedido_original,)
            # 14. CALCULA TROCO
            troco = Decimal('0.00')
            if (total_venda > 0 and total_pago > total_venda): troco = total_pago - total_venda
            # 15. STATUS DO PEDIDO
            if pix_pendente:
                pedido.situacao = 'Aberto'
                pedido.status_pagamento = 'pendente'
            else:
                pedido.situacao = 'Faturado'
                pedido.dt_fat = timezone.localtime(timezone.now())
                # Venda negativa = crédito gerado para o cliente.
                if pedido.total <= 0: pedido.status_pagamento = 'pago'
                elif total_pago >= pedido.total: pedido.status_pagamento = 'pago'
                elif total_pago > 0: pedido.status_pagamento = 'parcial'
                else: pedido.status_pagamento = 'pendente'
            pedido.save(update_fields=['situacao','status_pagamento','dt_fat',])
            # 16. REGISTRA LOG
            registrar_log(request=request,tipo="FATURAR",modulo="Pedido",objeto=pedido.codigo,objeto_id=pedido.id,descricao=(f"Faturou o pedido nº {pedido.codigo}"),
                alteracoes={"Valor Total": str(pedido.total),"Cliente": str(pedido.cli),"Vendedor": str(pedido.vendedor),"Caixa": str(pedido.caixa.terminal.nome),
                    "Forma de Pagamento": ", ".join(str(fp.forma_pgto) for fp in pedido.formas_pgto.all()),
                }
            )
            # 17. RESPOSTA
            return JsonResponse({'sucesso': True,'pedido_id': pedido.codigo,'total': float(total_venda),'pago': float(total_pago),'troco': float(troco),'pix_pendente': pix_pendente,})
    except ObjectDoesNotExist: erros.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        detalhe = str(e.__cause__ if e.__cause__ else e)
        erros.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {detalhe}")
    except DatabaseError as e: erros.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except ValueError as e: erros.append(f"<i class='fa-solid fa-xmark'></i> {str(e)}")
    except Exception as e: erros.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return JsonResponse({'erro': erros},status=500)

@login_required
def buscar_pedido_troca_devolucao(request):
    erros = []
    empresa = request.user.empresa
    try:
        with transaction.atomic():
            codigo = request.GET.get("codigo")
            if not codigo:
                erros.append("Informe o código do pedido.")
                return JsonResponse({"sucesso": False, "erro": erros})
            # 🔥Otimizado: Trocamos "itens__devolucoes" por "itens" já que faremos a query direta no PedidoDevolucaoItem para evitar o conflito do Django
            pedido = Pedido.objects.select_related("cli", "vinc_emp", "vinc_fil").prefetch_related("itens__produto").get(codigo=codigo, vinc_emp=empresa)
            if pedido.situacao != "Faturado":
                erros.append("Somente pedidos faturados podem ser trocados ou devolvidos.")
                return JsonResponse({"sucesso": False, "erro": erros})
            itens = []
            for i in pedido.itens.all():
                # 🔥 CORREÇÃO AQUI: Forçamos o Django a calcular a soma filtrando direto pela tabela associativa.
                # Isso ignora completamente a colisão de 'related_name' criada nos models.
                qtd_ja_devolvida = PedidoDevolucaoItem.objects.filter(item_pedido=i).aggregate(total=Sum("quantidade"))["total"] or Decimal("0")
                saldo = i.quantidade - qtd_ja_devolvida
                if saldo <= 0: continue
                itens.append({"item_id":i.id,"produto_id":i.produto.codigo,"codigo":i.codigo_usado or i.produto.codigo,"descricao":getattr(i.produto,"desc_prod",getattr(i.produto,"descricao",str(i.produto))),
                    "valor_unitario":float(i.vl_unit),"quantidade_vendida":float(i.quantidade),"quantidade_devolvida":float(qtd_ja_devolvida),"quantidade_disponivel":float(saldo),
                    "subtotal_disponivel":float(saldo * i.vl_unit),
                })
            # 🔥 Se passar por todos os itens e nenhum tiver saldo disponível para devolver
            if not itens:
                erros.append(f"O pedido nº {codigo} não possui nenhuma quantidade ou saldo disponível para ser devolvido.")
                return JsonResponse({"sucesso": False, "erro": erros})
            return JsonResponse({"sucesso": True,
                "pedido": {"id": pedido.id, "codigo": pedido.codigo, "cliente_id": pedido.cli.codigo,"cliente": pedido.nome_cli, "total": float(pedido.total),
                    "data": timezone.localtime(pedido.dt_fat).strftime("%d/%m/%Y %H:%M") if pedido.dt_fat else "",
                },"itens": itens
            })
    except Pedido.DoesNotExist: erros.append("Pedido não encontrado.")
    except ObjectDoesNotExist: erros.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        detalhe = str(e.__cause__ if e.__cause__ else e)
        erros.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {detalhe}")
    except DatabaseError as e: erros.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except ValueError as e: erros.append(f"<i class='fa-solid fa-xmark'></i> {str(e)}")
    except Exception as e: erros.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return JsonResponse({"sucesso": False, "erro": erros})

@login_required
@require_POST
def validar_itens_devolucao(request):
    """ Valida as quantidades a serem devolvidas baseando-se no 'codigo' do pedido da empresa. Retorna os dados formatados negativamente para o front-end injetar no carrinho. """
    erros = []
    empresa = request.user.empresa
    try:
        with transaction.atomic():
            dados = json.loads(request.body)
            codigo_pedido = dados.get("codigo_pedido")
            itens = dados.get("itens", [])  # Ex: [{"item_id": 12, "quantidade": 2}] (aqui usamos o ID do PedidoProduto para precisão da linha)
            if not codigo_pedido or not itens:
                erros.append("Dados incompletos para validação.")
                return JsonResponse({"sucesso": False, "erro": erros})
            # Busca o pedido original pelo CÓDIGO da empresa logada
            try:
                pedido_original = Pedido.objects.get(codigo=codigo_pedido, vinc_emp=empresa)
            except Pedido.DoesNotExist:
                erros.append("Pedido original não encontrado nesta empresa.")
                return JsonResponse({"sucesso": False, "erro": erros})
            itens_validados = []
            for it in itens:
                item_id = it.get("item_id")  # ID da linha do PedidoProduto
                qtd_devolver = Decimal(str(it.get("quantidade", 0)))
                if qtd_devolver <= 0:
                    continue
                # Garante que o item pertence ao pedido e à empresa correta
                item_pedido = PedidoProduto.objects.select_related('produto').get(id=item_id, pedido=pedido_original)
                # Calcula o histórico de devoluções deste item
                qtd_ja_devolvida = PedidoDevolucaoItem.objects.filter(item_pedido=item_pedido).aggregate(total=Sum("quantidade"))["total"] or Decimal("0")
                saldo_disponivel = item_pedido.quantidade - qtd_ja_devolvida
                if qtd_devolver > saldo_disponivel:
                    erros.append(f"Produto {item_pedido.produto.desc_prod} só possui {saldo_disponivel} unidades disponíveis para devolução.")
                    return JsonResponse({"sucesso": False, "erro": erros})
                # Monta a estrutura para o Front-end (com valores negativos)
                itens_validados.append({"item_pedido_id": item_pedido.id, "produto_id": item_pedido.produto.id,"codigo_produto": item_pedido.codigo_usado or item_pedido.produto.codigo,
                    "descricao": f"<i class='fa-solid fa-arrows-rotate text-primary-emphasis fa-spin me-1' title='Produto a ser devolvido'></i> {item_pedido.produto.desc_prod}",
                    "vl_unit": float(item_pedido.vl_unit), "quantidade": float(-qtd_devolver),"subtotal": float(-(qtd_devolver * item_pedido.vl_unit)), "is_devolucao": True
                })
            return JsonResponse({"sucesso": True, "itens": itens_validados})
    except ObjectDoesNotExist:erros.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        detalhe = str(e.__cause__ if e.__cause__ else e)
        erros.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {detalhe}")
    except DatabaseError as e:erros.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except ValueError as e:erros.append(f"<i class='fa-solid fa-xmark'></i> {str(e)}")
    except Exception as e:erros.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return JsonResponse({"sucesso": False, "erro": erros})

@login_required
@require_POST
def gerar_pagamento_caixa(request):
    erros = []
    empresa = request.user.empresa
    try:
        with transaction.atomic():
            data = json.loads(request.body)
            caixa_id = data.get("caixa_id")
            pagamentos_front = data.get("formas", [])
            if not caixa_id:
                erros.append("Caixa não informado")
                return JsonResponse({"erro": erros}, status=400)
            caixa = Caixa.objects.get(codigo=caixa_id, vinc_emp=empresa)
            if caixa.situacao != "Aberto":
                erros.append("Caixa fechado")
                return JsonResponse({"erro": erros}, status=400)
            if not pagamentos_front:
                erros.append("Nenhuma forma enviada")
                return JsonResponse({"erro": erros}, status=400)
            # 🔥 remove PIX pendente antigo (igual pedido)
            from django.contrib.contenttypes.models import ContentType
            Pagamento.objects.filter(content_type=ContentType.objects.get_for_model(caixa), object_id=caixa.codigo, status="pendente").delete()
            pagamentos_gerados = []
            for pg in pagamentos_front:
                forma = FormaPgto.objects.get(codigo=pg["forma"])
                valor = Decimal(str(pg["valor"]))
                gateway = (forma.gateway or "").strip().lower()
                if gateway in ["", "nenhum", "none"]: continue
                try:
                    service = PagamentoService(forma)
                    result = service.gerar_pagamento(valor=valor, descricao=f"Venda Caixa {caixa.codigo}", email=None, external_reference=str(caixa.codigo))
                    if not result: continue
                    txid = result.get("id")
                    qr_code = result.get("qr_code")
                    if not txid or not qr_code: continue
                    pagamento = Pagamento.objects.create(
                        vinc_emp=caixa.vinc_emp, content_type=ContentType.objects.get_for_model(caixa), object_id=caixa.codigo, forma_pgto=forma, valor=valor, txid=txid,
                        qr_code=qr_code, qr_base64=result.get("qr_base64"), gateway=forma.gateway, status="pendente"
                    )
                    pagamentos_gerados.append({"txid": pagamento.txid, "qr_code": pagamento.qr_code, "qr_base64": pagamento.qr_base64, "valor": str(pagamento.valor)})
                except Exception: continue
            return JsonResponse({"pagamentos": pagamentos_gerados})
    except ObjectDoesNotExist:
        erros.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        detalhe = str(e.__cause__ if e.__cause__ else e)
        erros.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {detalhe}")
    except DatabaseError as e:
        erros.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except ValueError as e:
        erros.append(f"<i class='fa-solid fa-xmark'></i> {str(e)}")
    except Exception as e:
        erros.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return JsonResponse({"erro": erros}, status=500)

@login_required
def status_pagamento_caixa(request, caixa_id):
    try:
        caixa = Caixa.objects.get(codigo=caixa_id, vinc_emp=request.user.empresa)
        pagamentos = Pagamento.objects.filter(content_type=ContentType.objects.get_for_model(caixa), object_id=caixa.codigo)
        if not pagamentos.exists(): return JsonResponse({"status": "sem_pagamento"})
        # 🔥 se qualquer um ainda estiver pendente
        if pagamentos.filter(status="pendente").exists(): return JsonResponse({"status": "pendente"})
        # 🔥 todos pagos
        if pagamentos.filter(status="pago").exists(): return JsonResponse({"status": "pago"})
        return JsonResponse({"status": "desconhecido"})
    except Caixa.DoesNotExist: return JsonResponse({"erro": "Caixa não encontrado"}, status=404)

@login_required
def dados_fechamento_caixa(request, caixa_id):
    try:
        caixa = Caixa.objects.get(codigo=caixa_id, vinc_emp=request.user.empresa)
        if caixa.situacao != 'Aberto':
            return JsonResponse({'erro': 'Caixa já está fechado.'}, status=400)
        movs = caixa.movimentos.select_related('forma_pagamento').filter(situacao='Ativo')
        totais = defaultdict(lambda: {'forma_id': None, 'descricao': '', 'total': 0.0})
        # Saldo inicial em dinheiro (abertura)
        for m in movs:
            fp = m.forma_pagamento
            if not fp:
                continue
            key = fp.codigo
            totais[key]['forma_id'] = fp.codigo
            totais[key]['descricao'] = fp.descricao.upper()
            if m.tipo == 'Entrada':
                totais[key]['total'] += float(m.valor)
            elif m.tipo == 'Saída':
                totais[key]['total'] -= float(m.valor)
        formas = [v for v in totais.values() if v['descricao']]
        return JsonResponse({'sucesso': True, 'formas': formas})
    except Caixa.DoesNotExist:
        return JsonResponse({'erro': 'Caixa não encontrado.'}, status=404)
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)

@login_required
@require_POST
def fechar_caixa(request, caixa_id):
    erros = []
    empresa = request.user.empresa
    try:
        data = json.loads(request.body)
        fechamentos = data.get('fechamentos', [])
        if not fechamentos:
            return JsonResponse({'erro': ['Nenhum fechamento informado.']}, status=400)
        with transaction.atomic():
            # 1. Busca e bloqueia o caixa
            caixa = (Caixa.objects.select_for_update().select_related('terminal', 'vinc_fil').get(codigo=caixa_id,vinc_emp=empresa))
            if caixa.situacao != 'Aberto':
                return JsonResponse({'erro': ['Caixa já está fechado.']}, status=400)
            # 2. Processa os fechamentos
            formas_registradas = []
            total_fechamento = Decimal('0.00')
            for item in fechamentos:
                forma_codigo = item.get('forma_codigo')
                if not forma_codigo:continue
                forma = FormaPgto.objects.get(codigo=forma_codigo,vinc_emp=empresa)
                valor_sistema = Decimal(str(item.get('valor_sistema', 0)))
                valor_informado = Decimal(str(item.get('valor_informado', 0)))
                diferenca = valor_informado - valor_sistema
                fechamento = CaixaFechamento.objects.create(caixa=caixa,forma_pagamento=forma,valor_registrado=valor_sistema,valor_informado=valor_informado,diferenca=diferenca,)
                formas_registradas.append(str(forma))
                total_fechamento += valor_informado
            if not formas_registradas:
                raise ValueError('Nenhuma forma de pagamento válida foi informada.')
            # 3. Fecha o caixa
            caixa.situacao = 'Fechado'
            caixa.data_fechamento = timezone.localtime(timezone.now())
            caixa.save(update_fields=['situacao','data_fechamento'])
            # 4. Registra o log
            registrar_log(request=request,tipo="FECHAMENTO",modulo="Caixa",objeto=caixa.codigo,objeto_id=caixa.id,descricao=(f"Realizou o fechamento do caixa: {caixa.codigo} - {caixa.terminal.nome}"),
                alteracoes={"Valor Total do Fechamento": str(total_fechamento),"Formas": ", ".join(formas_registradas),}
            )
        return JsonResponse({'sucesso': True,'mensagem': 'Caixa fechado com sucesso!'})
    except ObjectDoesNotExist:erros.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e:
        detalhe = str(e.__cause__ if e.__cause__ else e)
        erros.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {detalhe}")
    except DatabaseError as e:erros.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
    except (ValueError, TypeError, InvalidOperation) as e:erros.append(f"<i class='fa-solid fa-xmark'></i> {str(e)}")
    except Exception as e:erros.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return JsonResponse({'erro': erros}, status=500)