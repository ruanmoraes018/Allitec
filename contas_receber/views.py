import os
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from core.pagamentos.fluxo import gerar_pagamento_conta_receber
from util.parse_decimal import parse_decimal
from .models import ContaReceber, ContaReceberBaixaForma
from .forms import ContaReceberForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from django.db import transaction
from filiais.models import Filial
from decimal import Decimal
from datetime import timedelta, date, datetime
from django.db import DatabaseError, IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from formas_pgto.models import FormaPgto
from django.template.loader import render_to_string
from weasyprint import HTML
from util.pix import Payload
from django.http import HttpResponse
from util.logs import gerar_alteracoes, registrar_log
import json
from django.utils import timezone
from django.db.models import Sum
from pedidos.models import Pedido
from django.conf import settings
import re
from util.logo_impressao import img_base64
from PIL import Image
from io import BytesIO
import base64
from util.filiais import aplicar_filtro_filial

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('contas_receber.view_contareceber')
@login_required
def lista_contas_receber(request):
    fil = request.GET.get('fil')
    cli = request.GET.get('cl')
    sit = request.GET.get('sit', 'Aberta')
    dt_ini = request.GET.get('dt_ini')
    dt_fim = request.GET.get('dt_fim')
    por_dt = request.GET.get('p_dt')
    reg = request.GET.get('reg', '10')
    list_p = request.GET.get('list_p', 'dt_v')
    ordem = request.GET.get('ordem', 'vinc_fil__fantasia')
    empresa = request.user.empresa
    contas_receber = ContaReceber.objects.filter(vinc_emp=empresa)
    # Aplica a regra de acesso às filiais
    contas_receber, aguardando_filial = aplicar_filtro_filial(request, contas_receber)
    if not dt_ini and not dt_fim and not por_dt and not aguardando_filial:
        hoje = date.today()
        primeiro_dia = hoje.replace(day=1)
        if hoje.month == 12: ultimo_dia = hoje.replace(year=hoje.year + 1, month=1, day=1) - timedelta(days=1)
        else: ultimo_dia = hoje.replace(month=hoje.month + 1, day=1) - timedelta(days=1)
        contas_receber = contas_receber.filter(situacao='Aberta', data_vencimento__range=(primeiro_dia, ultimo_dia))
        dt_ini = primeiro_dia.strftime('%d/%m/%Y')
        dt_fim = ultimo_dia.strftime('%d/%m/%Y')
        por_dt = 'Sim'
        sit = 'Aberta'
    if sit in ['Aberta', 'Paga']: contas_receber = contas_receber.filter(situacao=sit)
    if por_dt == 'Sim' and dt_ini and dt_fim:
        try:
            dt_ini_dt = datetime.strptime(dt_ini, '%d/%m/%Y').date()
            dt_fim_dt = datetime.strptime(dt_fim, '%d/%m/%Y').date()
            if list_p == 'dt_v': contas_receber = contas_receber.filter(data_vencimento__range=(dt_ini_dt, dt_fim_dt))
            elif list_p == 'dt_e': contas_receber = contas_receber.filter(data_emissao__date__range=(dt_ini_dt, dt_fim_dt))
            elif list_p == 'dt_p': contas_receber = contas_receber.filter(data_pagamento__range=(dt_ini_dt, dt_fim_dt))
        except ValueError: contas_receber = ContaReceber.objects.none()
    if cli: contas_receber = contas_receber.filter(cliente__codigo=cli)
    if reg == 'todos': num_pagina = contas_receber.count() or 1
    else:
        try: num_pagina = int(reg) if int(reg) > 0 else 10
        except ValueError: num_pagina = 10
    contas_receber = contas_receber.order_by(ordem)
    paginator = Paginator(contas_receber, num_pagina)
    page = request.GET.get('page')
    contas_receber = paginator.get_page(page)
    tot_vencido = sum((o.saldo or Decimal("0.00")) for o in contas_receber.object_list if o.data_vencimento < date.today() and o.situacao == "Aberta")
    tot_vencer = sum((o.saldo or Decimal("0.00")) for o in contas_receber.object_list if o.data_vencimento >= date.today() and o.situacao == "Aberta")
    tot_j = sum((o.valor_juros or Decimal('0.00')) for o in contas_receber.object_list if o.situacao == 'Aberta')
    tot_m = sum((o.valor_multa or Decimal('0.00')) for o in contas_receber.object_list if o.situacao == 'Aberta')
    tot_g = tot_vencido + tot_vencer + tot_j + tot_m
    filiais = Filial.objects.filter(vinc_emp=request.user.empresa)
    formas_pgto = FormaPgto.objects.filter(vinc_emp=request.user.empresa)
    return render(request, 'contas_receber/lista.html', {
        'contas_receber': contas_receber, 'filiais': filiais, 'formas_pgto': formas_pgto, 'fil': fil,
        'cli': cli, 'sit': sit, 'dt_ini': dt_ini, 'dt_fim': dt_fim, 'p_dt': por_dt, 'list_p': list_p, 'ordem': ordem, 'reg': reg,
        'tot_vencido': tot_vencido, 'tot_vencer': tot_vencer, 'tot_j': tot_j, 'tot_m': tot_m, 'tot_g': tot_g,
    })

@login_required
def lista_contas_receber_ajax(request):
    term = request.GET.get('term', '')
    contas_receber = ContaReceber.objects.filter(vinc_fil__fantasia=term, vinc_emp=request.user.empresa)
    data = {'contas_receber': [{'id': cr.codigo, 'filial': cr.vinc_fil.fantasia, 'cliente': cr.cliente.fantasia} for cr in contas_receber]}
    return JsonResponse(data)

@login_required
def detalhes_conta_receber_ajax(request, codigo):
    try:
        cr = get_object_or_404(ContaReceber.objects.select_related('cliente', 'vinc_fil', 'forma_pgto', 'pedido', 'orcamento').prefetch_related('formas_baixa__forma_pgto'), codigo=codigo, vinc_emp=request.user.empresa)
        formas = []
        for i, f in enumerate(cr.formas_baixa.all(), start=1):
            formas.append({"item": f"{i:03}", "forma": f.forma_pgto.descricao, "valor": str(f.valor)})
        data = {
            "id": cr.codigo, "num_conta": cr.num_conta, "cliente": cr.cliente.fantasia, "filial": cr.vinc_fil.fantasia if cr.vinc_fil else "",
            "data_emissao": cr.data_emissao.strftime("%d/%m/%Y") if cr.data_emissao else "", "data_vencimento": cr.data_vencimento.strftime("%d/%m/%Y") if cr.data_vencimento else "",
            "data_pagamento": cr.data_pagamento.strftime("%d/%m/%Y") if cr.data_pagamento else "", "situacao": cr.situacao, "valor": str(cr.valor), "juros": str(cr.valor_juros),
            "multa": str(cr.valor_multa), "desconto": str(cr.desconto), "total": str(cr.valor_total), "saldo": str(cr.saldo), "dias_atraso": cr.dias_atraso,
            "vencido": cr.esta_vencido, "formas": formas, "obs": cr.observacao or "", "obs_internas": cr.obs_internas or "",
        }
        return JsonResponse(data)
    except ContaReceber.DoesNotExist: return JsonResponse({'error': 'Conta não encontrada'}, status=404)

@login_required
def add_conta_receber(request):
    if not request.user.has_perm('contas_receber.add_contareceber'):
        messages.info(request, 'Você não tem permissão para adicionar contas à receber.')
        return redirect('/contas_receber/lista/')
    error_messages = []
    if request.method == 'POST':
        form = ContaReceberForm(request.POST, empresa=request.user.empresa)
        if form.is_valid():
            try:
                cr = form.save(commit=False)
                cr.vinc_emp = request.user.empresa
                cr.valor = parse_decimal(request.POST.get('valor'))
                cr.data_emissao = datetime.now().date()
                cr.save()
                registrar_log(
                    request, "CRIAR", "Conta à Receber", cr.num_conta,
                    f"Adicionou a conta à receber: {cr.num_conta} - {cr.cliente.fantasia}",
                    cr.id, gerar_alteracoes(obj_novo=cr)
                )
                cid = str(cr.codigo)
                messages.success(request, 'Conta à Receber gerada com sucesso!')
                return redirect('/contas_receber/lista/?tp=cod&s=' + cid)
            except ObjectDoesNotExist: error_messages.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
            except IntegrityError as e:
                detalhe = str(e)
                if hasattr(e, '__cause__') and e.__cause__: detalhe = str(e.__cause__)
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {detalhe}")
            except DatabaseError as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
            except Exception as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
        else:
            for field in form:
                for error in field.errors: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
    else: form = ContaReceberForm(empresa=request.user.empresa)
    return render(request, 'contas_receber/add.html', {'form': form, 'error_messages': error_messages})

@login_required
def att_conta_receber(request, codigo):
    cr = get_object_or_404(ContaReceber, codigo=codigo, vinc_emp=request.user.empresa)
    it_old = ContaReceber.objects.get(codigo=cr.codigo, vinc_emp=request.user.empresa)
    form = ContaReceberForm(instance=cr, empresa=request.user.empresa)
    if not request.user.has_perm('contas_receber.change_contareceber'):
        messages.info(request, 'Você não tem permissão para editar contas à receber.')
        return redirect('/contas_receber/lista/')
    if request.method == 'POST':
        dt_o = cr.data_emissao
        form = ContaReceberForm(request.POST, instance=cr, empresa=request.user.empresa)
        if form.is_valid():
            cr.data_emissao = dt_o
            cr.valor = parse_decimal(request.POST.get('valor'))
            cr.save()
            registrar_log(
                request, "ALTERAR", "Conta à Receber", cr.num_conta,
                f"Alterou a conta à receber: {cr.num_conta} - {cr.cliente.fantasia}",
                cr.id, gerar_alteracoes(it_old, cr)
            )
            next_url = request.POST.get('next') or request.GET.get('next')
            cid = str(cr.codigo)
            messages.success(request, 'Conta à Receber atualizada com sucesso!')
            if next_url: return redirect(next_url)
            else: return redirect('/contas_receber/lista/?tp=cod&s=' + cid)
        else:
            error_messages = []
            for field in form:
                if field.errors: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'contas_receber/att.html', {'form': form, 'cr': cr, 'error_messages': error_messages})
    else:
        form = ContaReceberForm(instance=cr, empresa=request.user.empresa)
        return render(request, 'contas_receber/att.html', {'form': form, 'cr': cr})

@login_required
def del_conta_receber(request, codigo):
    if not request.user.has_perm('contas_receber.delete_contareceber'):
        messages.info(request, 'Você não tem permissão para deletar contas à receber.')
        return redirect('/contas_receber/lista/')
    cr = get_object_or_404(ContaReceber, codigo=codigo, vinc_emp=request.user.empresa)
    registrar_log(
        request, "EXCLUIR", "Conta à Receber", cr.num_conta,
        f"Excluiu a conta à receber: {cr.num_conta} - {cr.cliente.fantasia}",
        cr.id, gerar_alteracoes(obj_antigo=cr)
    )
    cr.delete()
    messages.success(request, 'Conta à Receber deletada com sucesso!')
    return redirect('/contas_receber/lista/')

@login_required
@transaction.atomic
def pagar_conta_receber(request, codigo):
    cr = get_object_or_404(ContaReceber, codigo=codigo, vinc_emp=request.user.empresa)
    if cr.situacao == 'Paga':
        messages.warning(request, 'Conta à Receber já está paga.')
        return redirect('/contas_receber/lista/')
    if request.method != 'POST':
        messages.error(request, 'Método inválido.')
        return redirect('/contas_receber/lista/')
    def dec(v):
        try:
            v = str(v or '0').strip()
            if ',' in v: v = v.replace('.', '').replace(',', '.')
            return Decimal(v)
        except: return Decimal('0.00')
    juros_final = dec(request.POST.get('juros'))
    multa_final = dec(request.POST.get('multa'))
    desconto_final = dec(request.POST.get('desconto'))
    forma_ids = request.POST.getlist('forma_id[]')
    forma_valores_raw = request.POST.getlist('forma_valor[]')
    if not forma_ids or len(forma_ids) != len(forma_valores_raw):
        messages.warning(request, 'Informe pelo menos uma forma de pagamento válida.')
        return redirect('/contas_receber/lista/')
    formas_processadas = []
    total_pago = Decimal('0.00')
    for forma_id, valor_raw in zip(forma_ids, forma_valores_raw):
        valor = dec(valor_raw)
        if valor <= 0: continue
        formas_processadas.append({'forma_id': forma_id,'valor': valor,})
        total_pago += valor
    if not formas_processadas:
        messages.warning(request, 'Nenhum valor válido foi informado para a baixa.')
        return redirect('/contas_receber/lista/')
    total_titulo = cr.valor + juros_final + multa_final - desconto_final
    if total_pago <= 0:
        messages.warning(request, 'O valor pago deve ser maior que zero.')
        return redirect('/contas_receber/lista/')
    if total_pago > total_titulo:
        messages.warning(request, 'O valor pago não pode ser maior que o total do título.')
        return redirect('/contas_receber/lista/')
    restante = total_titulo - total_pago
    cr.desconto = desconto_final
    cr.observacao = (cr.observacao or '') + f' Baixa de R$ {total_pago:.2f}.'
    if len(formas_processadas) == 1: cr.forma_pgto__codigo = formas_processadas[0]['forma_id']
    pagamentos = []
    for item in formas_processadas:
        forma = FormaPgto.objects.get(codigo=item["forma_id"], vinc_emp=request.user.empresa)
        pagamentos.append({"forma_pgto": forma, "valor": item["valor"]})
    saldo = cr.baixar(pagamentos=pagamentos, juros=juros_final, multa=multa_final, desconto=desconto_final)
    origem = "Gerado Manualmente"
    if cr.pedido:
        origem = f"Pedido Nº {cr.pedido.codigo}"
    elif cr.orcamento:
        origem = f"Orçamento Nº {cr.orcamento.codigo}"
    registrar_log(
        request=request, tipo="BAIXA", modulo="Contas a Receber", objeto=cr.num_conta,
        descricao=f"Realizou a baixa da conta à receber {cr.num_conta} - {cr.cliente.fantasia}",
        objeto_id=cr.id,
        alteracoes={
            "Cliente": cr.cliente.fantasia, "Origem": origem, "Parcela": cr.num_conta,
            "Valor Original": float(cr.valor), "Valor Recebido": float(cr.valor_pago),
            "Data do Recebimento": timezone.localdate().strftime("%d/%m/%Y"),
            "Forma(s) de Pagamento": ", ".join(fp.forma_pgto.descricao for fp in cr.formas_baixa.all()),
        }
    )
    tem_avista = any((p["forma_pgto"].tipo or "").strip().lower() == "a vista" for p in pagamentos)
    imp_recibo = (cr.vinc_fil.imp_recibo_cr or "Não").strip()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({
            "success": True, "codigo": cr.codigo, "tem_avista": tem_avista, "imp_recibo": imp_recibo,
            "url_recibo": reverse("recibo_cr", args=[cr.codigo]), "redirect": f"/contas_receber/lista/",
        })
    if saldo > 0:
        messages.success(request, f"Baixa parcial realizada. Saldo restante: R$ {saldo:.2f}.")
        return redirect(f"/contas_receber/lista/")
    else:
        messages.success(request, "Baixa realizada com sucesso.")
        return redirect('/contas_receber/lista/')

@login_required
@transaction.atomic
def estornar_conta_receber(request, codigo):
    cr = get_object_or_404(ContaReceber, codigo=codigo, vinc_emp=request.user.empresa)
    try:
        cr.estornar()
        registrar_log(
            request=request, tipo="ESTORNO", modulo="Contas à Receber", objeto=cr.num_conta,
            descricao=f"Estornou a conta à receber {cr.num_conta} - {cr.cliente.fantasia}",
            objeto_id=cr.id, alteracoes={"Motivo do Estorno": cr.motivo}
        )
    except ValueError as e:
        messages.warning(request, str(e))
    else:
        messages.success(request, "Estorno da conta à receber realizado com sucesso!")
    return redirect("/contas_receber/lista/")

@login_required
def gerar_pix_conta_receber(request, conta_id):
    conta = get_object_or_404(ContaReceber, codigo=conta_id, vinc_emp=request.user.empresa)
    if conta.situacao == "Paga": return JsonResponse({"erro": "Conta já paga"})
    formas_json = request.POST.get("formas", "[]")
    try: formas = json.loads(formas_json)
    except: return JsonResponse({"erro": "Formato inválido de formas"})
    if not formas: return JsonResponse({"erro": "Nenhuma forma enviada"})
    total = Decimal('0.00')
    forma_pix = None
    for f in formas:
        valor = Decimal(str(f.get("valor", 0)))
        forma_id = f.get("forma_id")
        if valor <= 0 or not forma_id: continue
        forma = FormaPgto.objects.filter(codigo=forma_id, vinc_emp=request.user.empresa).first()
        if not forma: continue
        total += valor
        if (forma.gateway or "").strip().lower() not in ["", "nenhum", "none"]: forma_pix = forma
    if not forma_pix: return JsonResponse({"erro": "Nenhuma forma com gateway encontrada"})
    if total <= 0: return JsonResponse({"erro": "Valor inválido"})
    pagamento = gerar_pagamento_conta_receber(conta, forma_pix, total)
    if not pagamento: return JsonResponse({"erro": "Falha ao gerar PIX"})
    return JsonResponse({"txid": pagamento.txid, "qr_code": pagamento.qr_code, "qr_base64": pagamento.qr_base64, "valor": str(total)})

@login_required
def status_pagamento_conta(request, conta_id):
    conta = get_object_or_404(ContaReceber, codigo=conta_id, vinc_emp=request.user.empresa)
    total_pago = conta.formas_baixa.aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    conta.valor_pago = total_pago
    if conta.saldo <= 0 and conta.valor_pago > 0:
        conta.situacao = "Paga"
        if not conta.data_pagamento: conta.data_pagamento = timezone.now().date()
    conta.save(update_fields=["valor_pago", "situacao", "data_pagamento"])
    total = conta.valor + conta.juros + conta.multa - conta.desconto
    parcial = conta.valor_pago > 0 and conta.valor_pago < total
    restante = total - conta.valor_pago
    return JsonResponse({"status": conta.situacao, "saldo": str(conta.saldo), "valor_pago": str(conta.valor_pago), "pago": conta.situacao == "Paga", "parcial": parcial, "restante": str(restante)})

@login_required
def imprimir_carne(request, codigo):
    empresa = request.user.empresa
    conta = get_object_or_404(ContaReceber.objects.select_related("pedido", "orcamento", "cliente", "vinc_fil", "vinc_fil__cidade_fil",), codigo=codigo, vinc_emp=empresa,)
    # Descobre a origem das parcelas
    if conta.pedido:
        documento = conta.pedido
        tipo_documento = "Pedido"
        contas = (ContaReceber.objects.filter(pedido=documento, situacao="Aberta").select_related("forma_pgto", "vinc_fil", "vinc_fil__cidade_fil",).order_by("data_vencimento"))
    elif conta.orcamento:
        documento = conta.orcamento
        tipo_documento = "Orçamento"
        contas = (ContaReceber.objects.filter(orcamento=documento, situacao="Aberta").select_related("forma_pgto", "vinc_fil", "vinc_fil__cidade_fil",).order_by("data_vencimento"))
    else:
        documento = None
        tipo_documento = "Conta a Receber"
        contas = (ContaReceber.objects.filter(pk=conta.pk).select_related("forma_pgto", "vinc_fil", "vinc_fil__cidade_fil",))
    if not contas.exists():
        return HttpResponse("Não existem parcelas em aberto.")
    contas_contexto = []
    total_parcelas = contas.count()
    for c in contas:
        if not c.vinc_fil.chave_pix:
            return HttpResponse(f'A filial "{c.vinc_fil}" não possui uma chave Pix cadastrada.')
        nome = c.vinc_fil.fantasia.strip().upper()
        cidade = c.vinc_fil.cidade_fil.nome_cidade.strip().upper()
        chave_pix = c.vinc_fil.chave_pix.strip()
        if c.vinc_fil.tp_chave == "Telefone":
            chave_pix = re.sub(r"\D", "", chave_pix)
            if not chave_pix.startswith("55"):
                chave_pix = "55" + chave_pix
            chave_pix = "+" + chave_pix
        txt_id = f"CR{c.codigo}"
        valor = f"{c.valor:.2f}"
        # Descrição do Pix
        if c.pedido:
            descricao = (f"Parcela {c.num_conta}-{total_parcelas} (Pedido Nº {c.pedido.codigo})")
        elif c.orcamento:
            descricao = (f"Parcela {c.num_conta}-{total_parcelas} (Orçamento Nº {c.orcamento.codigo})")
        else:
            descricao = (f"Conta a Receber {c.num_conta}")
        resultado = Payload(nome, chave_pix, valor, cidade, txt_id, descricao).gerarPayload()
        c.qr_code = resultado["qr_code"]
        c.pix_copia_cola = resultado["payload"]
        contas_contexto.append(c)
    lg_emp = img_base64(conta.vinc_fil.logo.path)
    html = render_to_string("contas_receber/carne.html", {"empresa": conta.vinc_fil, "cliente": conta.cliente, "documento": documento, "tipo_documento": tipo_documento, "contas": contas_contexto, "lg_emp": lg_emp,})
    pdf = HTML(string=html, base_url=settings.MEDIA_ROOT).write_pdf()
    response = HttpResponse(pdf, content_type="application/pdf")
    if documento:
        response["Content-Disposition"] = (f'inline; filename="Carnê {tipo_documento} {documento.codigo}.pdf"')
    else:
        response["Content-Disposition"] = (f'inline; filename="Carnê ContaReceber {conta.codigo}.pdf"')
    return response

@login_required
def recibo_cr(request, codigo):
    cr = get_object_or_404(ContaReceber.objects.select_related("cliente", "vinc_emp", "vinc_fil").prefetch_related("formas_baixa__forma_pgto"), codigo=codigo, vinc_emp=request.user.empresa)
    logo_base64 = None
    if cr.vinc_fil and cr.vinc_fil.logo:
        logo_path = os.path.join(settings.MEDIA_ROOT, str(cr.vinc_fil.logo))
        if os.path.exists(logo_path):
            with Image.open(logo_path) as img:
                if img.mode in ('RGBA', 'LA'):
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[-1])
                    img = bg
                else: img = img.convert("RGB")
                buffer = BytesIO()
                img.save(buffer, format="JPEG")
                logo_base64 = base64.b64encode(buffer.getvalue()).decode()
    total = Decimal("0.00")
    descricao = []
    for forma in cr.formas_baixa.all():
        if forma.forma_pgto.tipo == "A vista":
            total += forma.valor
        descricao.append(f"{forma.forma_pgto.descricao} - R$ {forma.valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    html = render_to_string("contas_receber/recibo.html", {"cr": cr, "cliente": cr.cliente, "filial": cr.vinc_fil, "total": total, "formas": descricao, "logo_base64": logo_base64}, request=request)
    pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="recibo_{cr.codigo}.pdf"'
    return response