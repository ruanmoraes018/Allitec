import os
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from util.parse_decimal import parse_decimal
from .models import ContaPagar
from .forms import ContaPagarForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from django.db import transaction
from filiais.models import Filial
from decimal import Decimal
from datetime import timedelta, date, datetime
from django.db import DatabaseError, IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from django.template.loader import render_to_string
from weasyprint import HTML
from django.http import HttpResponse
from util.logs import gerar_alteracoes, registrar_log
from django.utils import timezone
from django.conf import settings
from PIL import Image
from io import BytesIO
import base64
from util.filiais import aplicar_filtro_filial

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('contas_pagar.view_contapagar')
@login_required
def lista_contas_pagar(request):
    fil = request.GET.get('fil')
    forn = request.GET.get('forn')
    sit = request.GET.get('sit', 'Aberta')
    dt_ini = request.GET.get('dt_ini')
    dt_fim = request.GET.get('dt_fim')
    por_dt = request.GET.get('p_dt')
    reg = request.GET.get('reg', '10')
    list_p = request.GET.get('list_p', 'dt_v')
    ordem = request.GET.get('ordem', 'filial__fantasia')
    empresa = request.user.empresa
    contas_pagar = ContaPagar.objects.filter(empresa=empresa)
    # Aplica a regra de acesso às filiais
    contas_pagar, aguardando_filial = aplicar_filtro_filial(request, contas_pagar)
    if not dt_ini and not dt_fim and not por_dt and not aguardando_filial:
        hoje = date.today()
        primeiro_dia = hoje.replace(day=1)
        if hoje.month == 12: ultimo_dia = hoje.replace(year=hoje.year + 1, month=1, day=1) - timedelta(days=1)
        else: ultimo_dia = hoje.replace(month=hoje.month + 1, day=1) - timedelta(days=1)
        contas_pagar = contas_pagar.filter(situacao='Aberta', data_vencimento__range=(primeiro_dia, ultimo_dia))
        dt_ini = primeiro_dia.strftime('%d/%m/%Y')
        dt_fim = ultimo_dia.strftime('%d/%m/%Y')
        por_dt = 'Sim'
        sit = 'Aberta'
    if sit in ['Aberta', 'Paga']: contas_pagar = contas_pagar.filter(situacao=sit)
    if por_dt == 'Sim' and dt_ini and dt_fim:
        try:
            dt_ini_dt = datetime.strptime(dt_ini, '%d/%m/%Y').date()
            dt_fim_dt = datetime.strptime(dt_fim, '%d/%m/%Y').date()
            if list_p == 'dt_v': contas_pagar = contas_pagar.filter(data_vencimento__range=(dt_ini_dt, dt_fim_dt))
            elif list_p == 'dt_e': contas_pagar = contas_pagar.filter(data_emissao__date__range=(dt_ini_dt, dt_fim_dt))
            elif list_p == 'dt_p': contas_pagar = contas_pagar.filter(data_pagamento__range=(dt_ini_dt, dt_fim_dt))
        except ValueError: contas_pagar = ContaPagar.objects.none()
    if forn: contas_pagar = contas_pagar.filter(fornecedor__codigo=forn)
    if reg == 'todos': num_pagina = contas_pagar.count() or 1
    else:
        try: num_pagina = int(reg) if int(reg) > 0 else 10
        except ValueError: num_pagina = 10
    contas_pagar = contas_pagar.order_by(ordem)
    paginator = Paginator(contas_pagar, num_pagina)
    page = request.GET.get('page')
    contas_pagar = paginator.get_page(page)
    tot_vencido = sum((o.saldo or Decimal("0.00")) for o in contas_pagar.object_list if o.data_vencimento < date.today() and o.situacao == "Aberta")
    tot_vencer = sum((o.saldo or Decimal("0.00")) for o in contas_pagar.object_list if o.data_vencimento >= date.today() and o.situacao == "Aberta")
    tot_j = sum((o.valor_juros or Decimal('0.00')) for o in contas_pagar.object_list if o.situacao == 'Aberta')
    tot_m = sum((o.valor_multa or Decimal('0.00')) for o in contas_pagar.object_list if o.situacao == 'Aberta')
    tot_g = tot_vencido + tot_vencer + tot_j + tot_m
    filiais = Filial.objects.filter(vinc_emp=request.user.empresa)
    return render(request, 'contas_pagar/lista.html', {
        'contas_pagar': contas_pagar, 'filiais': filiais, 'fil': fil,
        'forn': forn, 'sit': sit, 'dt_ini': dt_ini, 'dt_fim': dt_fim, 'p_dt': por_dt, 'list_p': list_p, 'ordem': ordem, 'reg': reg,
        'tot_vencido': tot_vencido, 'tot_vencer': tot_vencer, 'tot_j': tot_j, 'tot_m': tot_m, 'tot_g': tot_g,
    })

@login_required
def lista_contas_pagar_ajax(request):
    term = request.GET.get('term', '')
    contas_pagar = ContaPagar.objects.filter(filial__fantasia=term, empresa=request.user.empresa)
    data = {'contas_pagar': [{'id': cp.codigo, 'filial': cp.filial.fantasia, 'fornecedor': cp.fornecedor.fantasia} for cp in contas_pagar]}
    return JsonResponse(data)

@login_required
def detalhes_conta_pagar_ajax(request, codigo):
    try:
        cp = get_object_or_404(ContaPagar.objects.select_related('fornecedor', 'filial'), codigo=codigo, empresa=request.user.empresa)
        data = {
            "id": cp.codigo, "num_conta": cp.num_conta, "fornecedor": cp.fornecedor.fantasia, "filial": cp.filial.fantasia if cp.filial else "",
            "data_emissao": cp.data_emissao.strftime("%d/%m/%Y") if cp.data_emissao else "", "data_vencimento": cp.data_vencimento.strftime("%d/%m/%Y") if cp.data_vencimento else "",
            "data_pagamento": cp.data_pagamento.strftime("%d/%m/%Y") if cp.data_pagamento else "", "situacao": cp.situacao, "valor": str(cp.valor), "juros": str(cp.valor_juros),
            "multa": str(cp.valor_multa), "desconto": str(cp.desconto), "total": str(cp.valor_total), "saldo": str(cp.saldo), "dias_atraso": cp.dias_atraso,
            "vencido": cp.esta_vencido, "obs": cp.observacao or "", "obs_internas": cp.obs_internas or "",
        }
        return JsonResponse(data)
    except ContaPagar.DoesNotExist: return JsonResponse({'error': 'Conta não encontrada'}, status=404)

@login_required
def add_conta_pagar(request):
    if not request.user.has_perm('contas_pagar.add_contapagar'):
        messages.info(request, 'Você não tem permissão para adicionar contas à pagar.')
        return redirect('/contas_pagar/lista/')
    error_messages = []
    if request.method == 'POST':
        form = ContaPagarForm(request.POST, empresa=request.user.empresa)
        if form.is_valid():
            try:
                cp = form.save(commit=False)
                cp.empresa = request.user.empresa
                cp.valor = parse_decimal(request.POST.get('valor'))
                cp.data_emissao = datetime.now().date()
                cp.save()
                registrar_log(
                    request, "CRIAR", "Conta à Pagar", cp.num_conta,
                    f"Adicionou a conta à pagar: {cp.num_conta} - {cp.fornecedor.fantasia}",
                    cp.id, gerar_alteracoes(obj_novo=cp)
                )
                cid = str(cp.codigo)
                messages.success(request, 'Conta à Pagar gerada com sucesso!')
                return redirect('/contas_pagar/lista/?tp=cod&s=' + cid)
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
    else: form = ContaPagarForm(empresa=request.user.empresa)
    return render(request, 'contas_pagar/add.html', {'form': form, 'error_messages': error_messages})

@login_required
def att_conta_pagar(request, codigo):
    cp = get_object_or_404(ContaPagar, codigo=codigo, empresa=request.user.empresa)
    it_old = ContaPagar.objects.get(codigo=cp.codigo, empresa=request.user.empresa)
    form = ContaPagarForm(instance=cp, empresa=request.user.empresa)
    if not request.user.has_perm('contas_pagar.change_contapagar'):
        messages.info(request, 'Você não tem permissão para editar contas à pagar.')
        return redirect('/contas_pagar/lista/')
    if request.method == 'POST':
        dt_o = cp.data_emissao
        form = ContaPagarForm(request.POST, instance=cp, empresa=request.user.empresa)
        if form.is_valid():
            cp.data_emissao = dt_o
            cp.valor = parse_decimal(request.POST.get('valor'))
            cp.save()
            registrar_log(
                request, "ALTERAR", "Conta à Pagar", cp.num_conta,
                f"Alterou a conta à pagar: {cp.num_conta} - {cp.fornecedor.fantasia}",
                cp.id, gerar_alteracoes(it_old, cp)
            )
            next_url = request.POST.get('next') or request.GET.get('next')
            cid = str(cp.codigo)
            messages.success(request, 'Conta à Pagar atualizada com sucesso!')
            if next_url: return redirect(next_url)
            else: return redirect('/contas_pagar/lista/?tp=cod&s=' + cid)
        else:
            error_messages = []
            for field in form:
                if field.errors: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'contas_pagar/att.html', {'form': form, 'cp': cp, 'error_messages': error_messages})
    else:
        form = ContaPagarForm(instance=cp, empresa=request.user.empresa)
        return render(request, 'contas_pagar/att.html', {'form': form, 'cp': cp})

@login_required
def del_conta_pagar(request, codigo):
    if not request.user.has_perm('contas_pagar.delete_contapagar'):
        messages.info(request, 'Você não tem permissão para deletar contas à pagar.')
        return redirect('/contas_pagar/lista/')
    cp = get_object_or_404(ContaPagar, codigo=codigo, empresa=request.user.empresa)
    registrar_log(
        request, "EXCLUIR", "Conta à Pagar", cp.num_conta,
        f"Excluiu a conta à pagar: {cp.num_conta} - {cp.fornecedor.fantasia}",
        cp.id, gerar_alteracoes(obj_antigo=cp)
    )
    cp.delete()
    messages.success(request, 'Conta à Pagar deletada com sucesso!')
    return redirect('/contas_pagar/lista/')

@login_required
@transaction.atomic
def pagar_conta_pagar(request, codigo):
    cp = get_object_or_404(ContaPagar, codigo=codigo, empresa=request.user.empresa)
    if cp.situacao == 'Paga':
        messages.warning(request, 'Conta à Pagar já está paga.')
        return redirect('/contas_pagar/lista/')
    if request.method != 'POST':
        messages.error(request, 'Método inválido.')
        return redirect('/contas_pagar/lista/')
    def dec(v):
        try:
            v = str(v or '0').strip()
            if ',' in v: v = v.replace('.', '').replace(',', '.')
            return Decimal(v)
        except: return Decimal('0.00')
    juros_final = dec(request.POST.get('juros'))
    multa_final = dec(request.POST.get('multa'))
    desconto_final = dec(request.POST.get('desconto'))
    total_pago = Decimal('0.00')
    total_titulo = cp.valor + juros_final + multa_final - desconto_final
    if total_pago <= 0:
        messages.warning(request, 'O valor pago deve ser maior que zero.')
        return redirect('/contas_pagar/lista/')
    if total_pago > total_titulo:
        messages.warning(request, 'O valor pago não pode ser maior que o total do título.')
        return redirect('/contas_pagar/lista/')
    restante = total_titulo - total_pago
    cp.desconto = desconto_final
    cp.observacao = (cp.observacao or '') + f' Baixa de R$ {total_pago:.2f}.'
    origem = "Gerado Manualmente"
    if cp.fornecedor:
        origem = f"Entrada de NF/Pedido Nº {cp.fornecedor.codigo}"
    registrar_log(
        request=request, tipo="BAIXA", modulo="Contas à Pagar", objeto=cp.num_conta,
        descricao=f"Realizou a baixa da conta à pagar {cp.num_conta} - {cp.fornecedor.fantasia}",
        objeto_id=cp.id,
        alteracoes={
            "Fornecedor": cp.fornecedor.fantasia, "Origem": origem, "Parcela": cp.num_conta,
            "Valor Original": float(cp.valor), "Valor Recebido": float(cp.valor_pago),
            "Data do Pagamento": timezone.localdate().strftime("%d/%m/%Y"),
        }
    )
    imp_recibo = (cp.filial.imp_recibo_cr or "Não").strip()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({
            "success": True, "codigo": cp.codigo, "imp_recibo": imp_recibo,
            "url_recibo": reverse("recibo_cr", args=[cp.codigo]), "redirect": f"/contas_pagar/lista/",
        })
    if restante > 0:
        messages.success(request, f"Baixa parcial realizada. Saldo restante: R$ {restante:.2f}.")
        return redirect(f"/contas_pagar/lista/")
    else:
        messages.success(request, "Baixa realizada com sucesso.")
        return redirect('/contas_pagar/lista/')

@login_required
@transaction.atomic
def estornar_conta_pagar(request, codigo):
    cp = get_object_or_404(ContaPagar, codigo=codigo, empresa=request.user.empresa)
    try:
        cp.estornar()
        registrar_log(
            request=request, tipo="ESTORNO", modulo="Contas à Pagar", objeto=cp.num_conta,
            descricao=f"Estornou a conta à pagar {cp.num_conta} - {cp.fornecedor.fantasia}",
            objeto_id=cp.id, alteracoes={"Motivo do Estorno": cp.motivo}
        )
    except ValueError as e:
        messages.warning(request, str(e))
    else:
        messages.success(request, "Estorno da conta à pagar realizado com sucesso!")
    return redirect("/contas_pagar/lista/")

@login_required
def recibo_cp(request, codigo):
    cp = get_object_or_404(ContaPagar.objects.select_related("fornecedor", "empresa", "filial"), codigo=codigo, empresa=request.user.empresa)
    logo_base64 = None
    if cp.filial and cp.filial.logo:
        logo_path = os.path.join(settings.MEDIA_ROOT, str(cp.filial.logo))
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
    html = render_to_string("contas_pagar/recibo.html", {"cp": cp, "fornecedor": cp.fornecedor, "filial": cp.filial, "total": total, "logo_base64": logo_base64}, request=request)
    pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="recibo_{cp.codigo}.pdf"'
    return response