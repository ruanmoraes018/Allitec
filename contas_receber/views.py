from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import ContaReceber, ContaReceberBaixaForma
from .forms import ContaReceberForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from django.db import transaction
from filiais.models import Usuario, Filial
from decimal import Decimal, InvalidOperation
from datetime import timedelta, date, datetime
from django.db import DatabaseError, IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from formas_pgto.models import FormaPgto
import re

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
    if not dt_ini and not dt_fim and not por_dt:
        hoje = date.today()
        primeiro_dia = hoje.replace(day=1)
        if hoje.month == 12:
            ultimo_dia = hoje.replace(year=hoje.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            ultimo_dia = hoje.replace(month=hoje.month + 1, day=1) - timedelta(days=1)
        contas_receber = contas_receber.filter(situacao='Aberta', data_vencimento__range=(primeiro_dia, ultimo_dia))
        dt_ini = primeiro_dia.strftime('%d/%m/%Y')
        dt_fim = ultimo_dia.strftime('%d/%m/%Y')
        por_dt = 'Sim'
        sit = 'Aberta'
    if sit in ['Aberta', 'Paga']:
        contas_receber = contas_receber.filter(situacao=sit)
    if por_dt == 'Sim' and dt_ini and dt_fim:
        try:
            dt_ini_dt = datetime.strptime(dt_ini, '%d/%m/%Y').date()
            dt_fim_dt = datetime.strptime(dt_fim, '%d/%m/%Y').date()
            if list_p == 'dt_v':
                contas_receber = contas_receber.filter(data_vencimento__range=(dt_ini_dt, dt_fim_dt))
            elif list_p == 'dt_e':
                contas_receber = contas_receber.filter(data_emissao__date__range=(dt_ini_dt, dt_fim_dt))
            elif list_p == 'dt_p':
                contas_receber = contas_receber.filter(data_pagamento__range=(dt_ini_dt, dt_fim_dt))
        except ValueError:
            contas_receber = ContaReceber.objects.none()
    if fil:
        contas_receber = contas_receber.filter(vinc_fil_id=fil)
    if cli:
        contas_receber = contas_receber.filter(cliente_id=cli)
    if reg == 'todos':
        num_pagina = contas_receber.count() or 1
    else:
        try:
            num_pagina = int(reg) if int(reg) > 0 else 10
        except ValueError:
            num_pagina = 10
    contas_receber = contas_receber.order_by(ordem)
    paginator = Paginator(contas_receber, num_pagina)
    page = request.GET.get('page')
    contas_receber = paginator.get_page(page)
    filiais = Filial.objects.filter(vinc_emp=request.user.empresa)
    formas_pgto = FormaPgto.objects.filter(vinc_emp=request.user.empresa)
    return render(request, 'contas_receber/lista.html', {
        'contas_receber': contas_receber, 'filiais': filiais, 'formas_pgto': formas_pgto, 'fil': fil,
        'cli': cli, 'sit': sit, 'dt_ini': dt_ini, 'dt_fim': dt_fim, 'p_dt': por_dt, 'list_p': list_p, 'ordem': ordem, 'reg': reg,
    })

@login_required
def lista_contas_receber_ajax(request):
    term = request.GET.get('term', '')
    contas_receber = ContaReceber.objects.filter(vinc_fil__fantasia=term, vinc_emp=request.user.empresa)
    data = {'contas_receber': [{'id': cr.id, 'filial': cr.vinc_fil.fantasia, 'cliente': cr.cliente.fantasia} for cr in contas_receber]}
    return JsonResponse(data)

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
                cr.save()
                cid = str(cr.id)
                messages.success(request, 'Conta à Receber gerada com sucesso!')
                return redirect('/contas_receber/lista/?tp=cod&s=' + cid)
            except ObjectDoesNotExist:
                error_messages.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
            except IntegrityError as e:
                detalhe = str(e)
                if hasattr(e, '__cause__') and e.__cause__:
                    detalhe = str(e.__cause__)
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {detalhe}")
            except DatabaseError as e:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco: {str(e)}")
            except Exception as e:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
        else:
            for field in form:
                for error in field.errors:
                    error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
    else:
        form = ContaReceberForm(empresa=request.user.empresa)
    return render(request, 'contas_receber/add.html', {'form': form, 'error_messages': error_messages})

@login_required
def att_conta_receber(request, id):
    cr = get_object_or_404(ContaReceber, pk=id, vinc_emp=request.user.empresa)
    form = ContaReceberForm(instance=cr, empresa=request.user.empresa)
    if not request.user.has_perm('contas_receber.change_contareceber'):
        messages.info(request, 'Você não tem permissão para editar contas à receber.')
        return redirect('/contas_receber/lista/')
    if request.method == 'POST':
        form = ContaReceberForm(request.POST, instance=cr, empresa=request.user.empresa)
        if form.is_valid():
            cr.save()
            next_url = request.POST.get('next') or request.GET.get('next')
            cid = str(cr.id)
            messages.success(request, 'Conta à Receber atualizada com sucesso!')
            if next_url:
                return redirect(next_url)
            else:
                return redirect('/contas_receber/lista/?tp=cod&s=' + cid)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'contas_receber/att.html', {'form': form, 'cr': cr, 'error_messages': error_messages})
    else:
        form = ContaReceberForm(instance=cr, empresa=request.user.empresa)
        return render(request, 'contas_receber/att.html', {'form': form, 'cr': cr})

@login_required
def del_conta_receber(request, id):
    if not request.user.has_perm('contas_receber.delete_contareceber'):
        messages.info(request, 'Você não tem permissão para deletar contas à receber.')
        return redirect('/contas_receber/lista/')
    cr = get_object_or_404(ContaReceber, pk=id, vinc_emp=request.user.empresa)
    cr.delete()
    messages.success(request, 'Conta à Receber deletada com sucesso!')
    return redirect('/contas_receber/lista/')

@login_required
@transaction.atomic
def pagar_conta_receber(request, id):
    cr = get_object_or_404(ContaReceber, pk=id, vinc_emp=request.user.empresa)
    if cr.situacao == 'Paga':
        messages.warning(request, 'Conta à Receber já está paga.')
        return redirect('/contas_receber/lista/')
    if request.method != 'POST':
        messages.error(request, 'Método inválido.')
        return redirect('/contas_receber/lista/')
    def dec(v):
        try:
            v = str(v or '0').strip()
            if ',' in v:
                v = v.replace('.', '').replace(',', '.')
            return Decimal(v)
        except (InvalidOperation, TypeError, AttributeError):
            return Decimal('0.00')
    juros_final = dec(request.POST.get('juros'))
    multa_final = dec(request.POST.get('multa'))
    desconto_final = dec(request.POST.get('desconto'))
    forma_ids = request.POST.getlist('forma_id[]')
    forma_valores_raw = request.POST.getlist('forma_valor[]')
    if not forma_ids or not forma_valores_raw or len(forma_ids) != len(forma_valores_raw):
        messages.warning(request, 'Informe pelo menos uma forma de pagamento válida.')
        return redirect('/contas_receber/lista/')
    formas_processadas = []
    total_pago = Decimal('0.00')
    for forma_id, valor_raw in zip(forma_ids, forma_valores_raw):
        valor = dec(valor_raw)
        if valor <= 0:
            continue
        formas_processadas.append({'forma_id': forma_id, 'valor': valor,})
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
    observacao_original = cr.observacao or ''
    cr.valor_pago = total_pago
    cr.desconto = desconto_final
    cr.data_pagamento = date.today()
    cr.situacao = 'Paga'
    cr.observacao = (f'{observacao_original}. Baixa realizada no valor de R$ {total_pago:.2f}.').strip()
    if len(formas_processadas) == 1:
        cr.forma_pgto_id = formas_processadas[0]['forma_id']
    cr.save()
    for item in formas_processadas:
        ContaReceberBaixaForma.objects.create(vinc_emp=request.user.empresa, conta_receber=cr, forma_pgto_id=item['forma_id'], valor=item['valor'],)
    if restante > 0:
        base_num = (cr.num_conta or str(cr.id)).strip()
        base_limpa = re.sub(r'\(R\d+\)$', '', base_num).strip()
        sufixo = 1
        novo_num = f'{base_limpa}(R{sufixo})'
        while ContaReceber.objects.filter(vinc_emp=cr.vinc_emp, num_conta=novo_num).exists():
            sufixo += 1
            novo_num = f'{base_limpa}(R{sufixo})'
        ContaReceber.objects.create(vinc_emp=cr.vinc_emp, vinc_fil=cr.vinc_fil, orcamento=cr.orcamento, pedido=cr.pedido, cliente=cr.cliente,
            forma_pgto=None, num_conta=novo_num, tp_juros=cr.tp_juros, tp_multa=cr.tp_multa, valor=restante, valor_pago=Decimal('0.00'),
            juros=cr.juros, multa=cr.multa, desconto=Decimal('0.00'), data_vencimento=cr.data_vencimento, situacao='Aberta',
            observacao=f'Saldo remanescente gerado a partir da baixa parcial do título {cr.num_conta}.'
        )
        messages.success(request, f'Baixa parcial realizada com sucesso. Novo título gerado com saldo de R$ {restante:.2f}.')
    else:
        messages.success(request, 'Baixa realizada com sucesso.')
    return redirect('/contas_receber/lista/')

@login_required
def estornar_conta_receber(request, id):
    cr = get_object_or_404(ContaReceber, pk=id, vinc_emp=request.user.empresa)
    if cr.situacao == 'Aberta':
        messages.warning(request, 'Contas à Receber Abertas não podem ser estornadas!')
        return redirect('/contas_receber/lista/')
    elif cr.situacao == 'Paga':
        cr.situacao = "Aberta"
        cr.save()
        messages.success(request, 'Estorno da Conta à Receber realizada com sucesso!')
        return redirect('/contas_receber/lista/')