from datetime import datetime, timedelta, time
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Orcamento, OrcamentoProduto, OrcamentoAdicional, OrcamentoFormaPgto
from formas_pgto.models import FormaPgto
from .forms import OrcamentoForm
import unicodedata
from django.http import JsonResponse, HttpResponseForbidden
import json
from reportlab.pdfgen import canvas
from io import BytesIO
from django.http import HttpResponse
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
import os
from django.conf import settings
from util.permissoes import verifica_permissao
from PIL import Image
import ast
from clientes.models import Cliente
from tecnicos.models import Tecnico
from django.views.decorators.http import require_POST
from produtos.models import Produto
from reportlab.lib import colors
from notifications.signals import notify
from filiais.models import Filial, Usuario
from orcamentos.models import SolicitacaoPermissao
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from notifications.models import Notification
from decimal import Decimal, InvalidOperation
import locale
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph

def enviar_solicitacao(request):
    acao = request.POST.get('acao')
    usuario_destino_id = request.POST.get('usuario_id')
    if not usuario_destino_id: return JsonResponse({'error': 'ID do usuário destino não enviado.'}, status=400)
    try: usuario_destino = User.objects.get(id=usuario_destino_id)
    except User.DoesNotExist: return JsonResponse({'error': 'Usuário destino não encontrado.'}, status=404)
    try: usuario_logado = Usuario.objects.get(user=request.user)
    except Usuario.DoesNotExist: return JsonResponse({'error': 'Usuário logado não possui perfil vinculado.'}, status=404)
    try: usuario_destino_ext = Usuario.objects.get(user=usuario_destino)
    except Usuario.DoesNotExist: return JsonResponse({'error': 'Usuário destino não possui perfil vinculado.'}, status=404)
    if usuario_logado.filial != usuario_destino_ext.filial: return HttpResponseForbidden('Usuário destino não pertence à sua filial.')
    expiracao = timezone.now() + timedelta(minutes=3)
    solicitacao = SolicitacaoPermissao.objects.create(solicitante=request.user, autorizado_por=usuario_destino, acao=acao, expira_em=expiracao)
    data_formatada = timezone.localtime(solicitacao.expira_em).strftime('%d/%m/%Y %H:%M')
    notify.send(request.user, recipient=usuario_destino, verb=f'Solicitação de permissão ID {solicitacao.id} - {data_formatada}', description=f'{request.user.last_name } solicitou permissão para {acao.replace("_", " ")}', data={'solicitacao_id': solicitacao.id})
    return JsonResponse({'status': 'enviado', 'id': solicitacao.id, 'expira_em': solicitacao.expira_em.isoformat()})

def verificar_status_solicitacao(request, solicitacao_id):
    try: solicitacao = SolicitacaoPermissao.objects.get(id=solicitacao_id)
    except SolicitacaoPermissao.DoesNotExist: return JsonResponse({'status': 'nao_encontrada'})
    if timezone.now() > solicitacao.expira_em and solicitacao.status == 'Pendente':
        solicitacao.status = 'Expirada'
        solicitacao.save()
    return JsonResponse({'status': solicitacao.status})

@csrf_exempt
def responder_solicitacao(request):
    solicitacao_id = request.POST.get('id')
    acao = request.POST.get('acao')  # 'aprovar' ou 'negar'
    if not solicitacao_id: return JsonResponse({'error': 'ID da solicitação não enviado'}, status=400)
    try: solicitacao = SolicitacaoPermissao.objects.get(id=solicitacao_id)
    except SolicitacaoPermissao.DoesNotExist: return JsonResponse({'error': 'Solicitação não encontrada'}, status=404)
    if acao == 'aprovar': solicitacao.status = 'Aprovada'
    elif acao == 'negar': solicitacao.status = 'Negada'
    else: return JsonResponse({'error': 'Ação inválida'}, status=400)
    solicitacao.save()
    # Marcar notificação como lida
    notifications = Notification.objects.filter(recipient=solicitacao.autorizado_por, verb__icontains=f'ID {solicitacao.id}', unread=True)
    notifications.update(unread=False)
    return JsonResponse({'status': solicitacao.status})

@login_required
def usuarios_com_permissao(request):
    try:
        usuario_logado = Usuario.objects.get(user=request.user)
        filial = usuario_logado.filial
    except Usuario.DoesNotExist: return JsonResponse({'usuarios': []})  # Usuário logado não possui vínculo
    usuarios = Usuario.objects.filter(gerar_senha_lib=True, filial=filial).select_related('user')
    lista = [{'id': u.user.id, 'nome': u.user.get_full_name() or u.user.username} for u in usuarios]
    return JsonResponse({'usuarios': lista})

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('orcamentos.view_orcamento')
@login_required
def lista_orcamentos(request):
    s = request.GET.get('s')
    f_s = request.GET.get('sit')
    tp_dt = request.GET.get('tp_dt')
    dt_ini = request.GET.get('dt_ini')
    dt_fim = request.GET.get('dt_fim')
    por_dt = request.GET.get('p_dt')
    fil = request.GET.get('fil')
    cli = request.GET.get('cl')
    tec = request.GET.get('tec')
    reg = request.GET.get('reg', '10')
    hoje = datetime.today().date()
    inicio_dia = datetime.combine(hoje, time.min)
    fim_dia = datetime.combine(hoje, time.max)
    ordem = request.GET.get('ordem', 'num_orcamento')
    # BASE — com otimizações
    orcamentos = (
        Orcamento.objects
        .filter(vinc_emp=request.user.empresa)
        .select_related('cli', 'vinc_fil', 'solicitante')
        .prefetch_related('formas_pgto__formas_pgto')
    )
    # Filtro por número
    if s:
        orcamentos = orcamentos.filter(num_orcamento__icontains=s)
    # Filtro por data
    if por_dt == 'Sim' and dt_ini and dt_fim:
        try:
            dt_ini_dt = datetime.combine(datetime.strptime(dt_ini, '%d/%m/%Y').date(), time.min)
            dt_fim_dt = datetime.combine(datetime.strptime(dt_fim, '%d/%m/%Y').date(), time.max)
            if tp_dt == 'Emissão':
                orcamentos = orcamentos.filter(dt_emi__range=(dt_ini_dt, dt_fim_dt))
            elif tp_dt == 'Entrega':
                orcamentos = orcamentos.filter(dt_ent__range=(dt_ini_dt, dt_fim_dt))
            elif tp_dt == 'Fatura':
                orcamentos = orcamentos.filter(dt_fat__range=(dt_ini_dt, dt_fim_dt))
        except ValueError:
            orcamentos = Orcamento.objects.none()
    # Filtro automático do dia
    filtros_ativos = any([s, f_s, por_dt == 'Sim', cli, tec, tp_dt and tp_dt != 'Todos'])
    if not filtros_ativos:
        orcamentos = orcamentos.filter(dt_emi__range=(inicio_dia, fim_dia), situacao='Aberto')
    # Situação
    if f_s and f_s != 'Todos':
        orcamentos = orcamentos.filter(situacao=f_s)
    # Filial
    if fil:
        orcamentos = orcamentos.filter(vinc_fil_id=fil)
    # Cliente
    if cli:
        orcamentos = orcamentos.filter(cli_id=cli)
    # Técnico
    if tec:
        orcamentos = orcamentos.filter(solicitante_id=tec)
    # Ordenação final
    if ordem == '0': orcamentos = orcamentos.order_by('num_orcamento')
    elif ordem == '1': orcamentos = orcamentos.order_by('vinc_fil')
    elif ordem == '2': orcamentos = orcamentos.order_by('cli')
    elif ordem == '3': orcamentos = orcamentos.order_by('solicitante')
    elif ordem == '4': orcamentos = orcamentos.order_by('situacao')
    elif ordem == '5': orcamentos = orcamentos.order_by('dt_emi')
    elif ordem == '6': orcamentos = orcamentos.order_by('dt_ent')
    elif ordem == '7': orcamentos = orcamentos.order_by('dt_fat')
    # Paginação
    if reg == 'todos':
        num_pagina = orcamentos.count() or 1
    else:
        try:
            num_pagina = int(reg) if int(reg) > 0 else 10
        except ValueError:
            num_pagina = 10
    paginator = Paginator(orcamentos, num_pagina)
    page = request.GET.get('page')
    orcamentos = paginator.get_page(page)
    return render(request, 'orcamentos/lista.html', {
        'orcamentos': orcamentos,
        's': s,
        'fil': fil,
        'cli': cli,
        'tec': tec,
        'dt_ini': dt_ini,
        'dt_fim': dt_fim,
        'p_dt': por_dt,
        'tp_dt': tp_dt,
        'reg': reg,
        'ordem': ordem,
        'filiais': Filial.objects.filter(vinc_emp=request.user.empresa),
        'clientes': Cliente.objects.filter(vinc_emp=request.user.empresa),
        'tecnicos': Tecnico.objects.filter(vinc_emp=request.user.empresa),
    })

@login_required
def add_orcamento(request):
    if not request.user.has_perm('orcamentos.add_orcamento'):
        messages.info(request, 'Você não tem permissão para adicionar orçamentos.')
        return redirect('/orcamentos/lista/')
    if request.method == 'POST':
        form = OrcamentoForm(request.POST)
        if form.is_valid():
            dt_emi = form.cleaned_data['dt_emi']  # Substitua 'dt_emi' pelo nome do campo correto
            hora_atual = datetime.now()  # Isso traz a data e a hora atuais no formato datetime
            hora_atual_ajustada = hora_atual - timedelta(hours=3)
            hora_atual_ajustada = hora_atual_ajustada.time()
            data_hora_completa = datetime.combine(dt_emi, hora_atual_ajustada)
            o = form.save(commit=False)
            o.dt_emi = data_hora_completa
            o.qtd_lam = request.POST.get("qtd_lam")
            o.situacao = 'Aberto'
            agora = datetime.now()
            if request.user.is_authenticated:
                o.vinc_emp = request.user.empresa
            o.save()
            o.num_orcamento = agora.strftime('%Y-') + str(o.id)
            o.save()
            # Produtos principais
            itens_prod = request.POST.get('itens_prod')
            if itens_prod:
                for item in json.loads(itens_prod):
                    try:
                        prod = Produto.objects.get(pk=item["codProd"])
                        OrcamentoProduto.objects.create(
                            orcamento=o,
                            produto=prod,
                            quantidade=Decimal(str(item.get("qtdProd", "0")).replace(",", "."))
                        )
                    except Produto.DoesNotExist:
                        continue
            # Produtos adicionais
            itens_prod_adc = request.POST.get('itens_prod_adc')
            if itens_prod_adc:
                for item in json.loads(itens_prod_adc):
                    try:
                        prod = Produto.objects.get(pk=item["codProd"])
                        OrcamentoAdicional.objects.create(
                            orcamento=o,
                            produto=prod,
                            quantidade=Decimal(str(item.get("qtdProd", "0")).replace(",", "."))
                        )
                    except Produto.DoesNotExist:
                        continue
            # Formas de pagamento
            itens_forma_pgto = request.POST.get('itens_forma_pgto')
            if itens_forma_pgto:
                for forma in json.loads(itens_forma_pgto):
                    try:
                        fpgto = FormaPgto.objects.get(descricao=forma["forma"])
                        OrcamentoFormaPgto.objects.create(
                            orcamento=o,
                            formas_pgto=fpgto,
                            valor=Decimal(str(forma.get("valor", "0")).replace(",", "."))
                        )
                    except FormaPgto.DoesNotExist:
                        continue
            o.atualizar_subtotal()
            o.save(update_fields=['subtotal'])
            messages.success(request, 'Orçamento adicionado com sucesso!')
            return redirect('/orcamentos/lista/?s=' + str(o.id))
        else:
            error_messages = [f"Campo ({field.label}) é obrigatório!" for field in form if field.errors]
            return render(request, 'orcamentos/add_orcamento.html', {'form': form, 'error_messages': error_messages})
    else:
        form = OrcamentoForm()
    return render(request, 'orcamentos/add_orcamento.html', {'form': form})

@login_required
def att_orcamento(request, id):
    orcamento = get_object_or_404(Orcamento, pk=id)
    if not request.user.has_perm('orcamentos.change_orcamento'):
        messages.info(request, 'Você não tem permissão para editar orçamentos.')
        return redirect('/orcamentos/lista/')
    if orcamento.situacao != 'Aberto':
        messages.warning(request, 'Orçamentos só podem ser alterados com status Aberto!')
        return redirect('/orcamentos/lista/?s=' + str(orcamento.id))
    form = OrcamentoForm(instance=orcamento)
    if request.method == 'POST':
        form = OrcamentoForm(request.POST, instance=orcamento)
        agora = datetime.now()
        if form.is_valid():
            dt_emi = form.cleaned_data['dt_emi']  # Substitua 'dt_emi' pelo nome do campo correto
            hora_atual = datetime.now()  # Isso traz a data e a hora atuais no formato datetime
            hora_atual_ajustada = hora_atual - timedelta(hours=3)
            hora_atual_ajustada = hora_atual_ajustada.time()
            data_hora_completa = datetime.combine(dt_emi, hora_atual_ajustada)

            orcamento.dt_emi = data_hora_completa
            orcamento.qtd_lam = request.POST.get("qtd_lam")
            orcamento.save()
            itens_prod = request.POST.get('itens_prod')
            if itens_prod:
                # Primeiro, exclua os produtos principais existentes para o orçamento
                OrcamentoProduto.objects.filter(orcamento=orcamento).delete()
                for item in json.loads(itens_prod):
                    try:
                        prod = Produto.objects.get(pk=item["codProd"])
                        OrcamentoProduto.objects.create(
                            orcamento=orcamento,
                            produto=prod,
                            quantidade=Decimal(str(item.get("qtdProd", "0")).replace(",", "."))
                        )
                    except Produto.DoesNotExist:
                        continue
            itens_prod_adc = request.POST.get('itens_prod_adc')
            if itens_prod_adc:
                # Primeiro, exclua os produtos adicionais existentes para o orçamento
                OrcamentoAdicional.objects.filter(orcamento=orcamento).delete()
                # Em seguida, adicione os novos produtos adicionais
                for item in json.loads(itens_prod_adc):
                    try:
                        prod = Produto.objects.get(pk=item["codProd"])
                        OrcamentoAdicional.objects.create(
                            orcamento=orcamento,
                            produto=prod,
                            quantidade=Decimal(str(item.get("qtdProd", "0")).replace(",", "."))
                        )
                    except Produto.DoesNotExist:
                        continue
            itens_forma_pgto = request.POST.get('itens_forma_pgto')
            if itens_forma_pgto:
                formas_atualizadas = set()
                for forma in json.loads(itens_forma_pgto):
                    try:
                        fpgto = FormaPgto.objects.get(descricao=forma["forma"])
                        formas_atualizadas.add(fpgto.id)  # Armazena o ID da forma de pagamento
                        # Verifica se a forma de pagamento já existe para o orçamento
                        existing_item = OrcamentoFormaPgto.objects.filter(orcamento=orcamento, formas_pgto=fpgto).first()
                        if existing_item:
                            # Atualiza o valor se já existir
                            existing_item.valor = Decimal(str(forma.get("valor", "0")).replace(",", "."))
                            existing_item.save()
                        else:
                            # Caso contrário, cria uma nova entrada
                            OrcamentoFormaPgto.objects.create(
                                orcamento=orcamento,
                                formas_pgto=fpgto,
                                valor=Decimal(str(forma.get("valor", "0")).replace(",", "."))
                            )
                    except FormaPgto.DoesNotExist:
                        continue
                # Remover as formas de pagamento que não estão mais na lista
                OrcamentoFormaPgto.objects.filter(orcamento=orcamento).exclude(formas_pgto__id__in=formas_atualizadas).delete()
            orcamento.num_orcamento = agora.strftime('%Y-') + str(orcamento.id)
            orcamento.save()
            orcamento.atualizar_subtotal()
            orcamento.save(update_fields=['subtotal'])
            messages.success(request, 'O.S. atualizada com sucesso!')
            return redirect('/orcamentos/lista/?s=' + str(orcamento.id))
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'orcamentos/att_orcamento.html', {
                'form': form,
                'orcamento': orcamento,
                'error_messages': error_messages
            })
    else:
        return render(request, 'orcamentos/att_orcamento.html', {
            'form': form,
            'orcamento': orcamento
        })

@login_required
def clonar_orcamento(request, id):
    orcamento = get_object_or_404(Orcamento, pk=id)
    if not request.user.has_perm('orcamentos.clonar_orcamento'):
        messages.info(request, 'Você não tem permissão para clonar orçamentos.')
        return redirect('/orcamentos/lista/')
    if request.method == 'POST':
        form = OrcamentoForm(request.POST)
        if form.is_valid():
            agora = datetime.now()
            # cria novo orçamento com os dados do formulário
            novo_orcamento = form.save(commit=False)
            novo_orcamento.vinc_fil = orcamento.vinc_fil  # mantém empresa
            novo_orcamento.situacao = 'Aberto'  # sempre Aberto
            novo_orcamento.save()
            novo_orcamento.num_orcamento = agora.strftime('%Y-') + str(novo_orcamento.id)
            novo_orcamento.save()
            # clona produtos principais
            for item in OrcamentoProduto.objects.filter(orcamento=orcamento):
                OrcamentoProduto.objects.create(
                    orcamento=novo_orcamento,
                    produto=item.produto,
                    quantidade=item.quantidade
                )
            # clona produtos adicionais
            for item in OrcamentoAdicional.objects.filter(orcamento=orcamento):
                OrcamentoAdicional.objects.create(
                    orcamento=novo_orcamento,
                    produto=item.produto,
                    quantidade=item.quantidade
                )
            # clona formas de pagamento
            for item in OrcamentoFormaPgto.objects.filter(orcamento=orcamento):
                OrcamentoFormaPgto.objects.create(
                    orcamento=novo_orcamento,
                    formas_pgto=item.formas_pgto,
                    valor=item.valor
                )
            novo_orcamento.atualizar_subtotal()
            novo_orcamento.save(update_fields=['subtotal'])
            messages.success(request, 'O.S. clonada com sucesso!')
            return redirect('/orcamentos/lista/?s=' + str(novo_orcamento.id))
        else:
            error_messages = []
            for field in form:
                for error in field.errors:
                    error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'orcamentos/clonar_orcamento.html', {
                'form': form,
                'error_messages': error_messages,
                'orcamento': orcamento
            })
    else:
        # GET: inicializa formulário com os dados do orçamento original
        initial_data = {
            'cli': orcamento.cli,
            'solicitante': orcamento.solicitante,
            'fantasia_emp': orcamento.fantasia_emp,
            'nome_cli': orcamento.nome_cli,
            'nome_solicitante': orcamento.nome_solicitante,
            'obs_cli': orcamento.obs_cli,
            'qtd': orcamento.qtd,
            'tp_lamina': orcamento.tp_lamina,
            'tp_vao': orcamento.tp_vao,
            'larg': orcamento.larg,
            'alt': orcamento.alt,
            'pintura': orcamento.pintura,
            'cor': orcamento.cor,
            'fator_peso': orcamento.fator_peso,
            'peso': orcamento.peso,
            'eixo_motor': orcamento.eixo_motor,
            'larg_corte': orcamento.larg_corte,
            'alt_corte': orcamento.alt_corte,
            'rolo': orcamento.rolo,
            'm2': orcamento.m2,
            'obs_form_pgto': orcamento.obs_form_pgto,
            'desconto': orcamento.desconto,
            'acrescimo': orcamento.acrescimo,
            'total': orcamento.total,
            'dt_emi': orcamento.dt_emi.strftime('%d/%m/%Y') if orcamento.dt_emi else '',
            'dt_ent': orcamento.dt_ent.strftime('%d/%m/%Y') if orcamento.dt_ent else '',
            'motivo': orcamento.motivo,
        }
        form = OrcamentoForm(initial=initial_data)
        return render(request, 'orcamentos/clonar_orcamento.html', {
            'form': form,
            'orcamento': orcamento
        })

@login_required
def del_orcamento(request, id):
    if not request.user.has_perm('orcamentos.delete_orcamento'):
        messages.info(request, 'Você não tem permissão para deletar orçamentos.')
        return redirect('/orcamentos/lista/')
    o = get_object_or_404(Orcamento, pk=id)
    if o.situacao == 'Faturado' or o.situacao == 'Cancelado':
        messages.warning(request, 'Orçamentos só podem ser deletados com status Aberto!')
        return redirect('/orcamentos/lista/?s=' + str(o.id))
    o.delete()
    messages.success(request, 'Orçamento deletado com sucesso!')
    return redirect('/orcamentos/lista/')

@require_POST
@login_required
def faturar_orcamento(request, id):
    orcamento = get_object_or_404(Orcamento, pk=id)
    if not request.user.has_perm('orcamentos.faturar_orcamento'):
        return JsonResponse({'status': 'erro', 'mensagem': 'Você não tem permissão para faturar orçamentos!'})
    if orcamento.situacao != 'Faturado':
        # baixa de estoque produtos
        for item in orcamento.produtos.all():
            produto = item.produto
            produto.estoque_prod -= item.quantidade
            produto.save()
        # baixa de estoque adicionais
        for item in orcamento.adicionais.all():
            produto = item.produto
            produto.estoque_prod -= item.quantidade
            produto.save()
        orcamento.situacao = "Faturado"
        hj = datetime.now()
        orcamento.dt_fat = hj
        orcamento.save()
        return JsonResponse({'status': 'ok', 'mensagem': f"Orçamento {orcamento.num_orcamento} faturado com sucesso."})
    else:
        return JsonResponse({'status': 'info', 'mensagem': f"Orçamento {orcamento.num_orcamento} já estava faturado."})

@require_POST
@login_required
def cancelar_orcamento(request, id):
    orcamento = get_object_or_404(Orcamento, pk=id)
    if not request.user.has_perm('orcamentos.cancelar_orcamento'):
        return JsonResponse({'status': 'erro', 'mensagem': 'Você não tem permissão para cancelar orçamentos!'})
    motivo = request.POST.get('motivo', '').strip()
    if not motivo:
        return JsonResponse({'status': 'erro', 'mensagem': 'Motivo do cancelamento é obrigatório.'})
    if orcamento.situacao == 'Faturado':
        # devolução estoque
        for item in orcamento.produtos.all():
            produto = item.produto
            produto.estoque_prod += item.quantidade
            produto.save()
        for item in orcamento.adicionais.all():
            produto = item.produto
            produto.estoque_prod += item.quantidade
            produto.save()
    orcamento.motivo = motivo
    orcamento.situacao = "Cancelado"
    orcamento.save()
    return JsonResponse({'status': 'ok', 'mensagem': f"Orçamento {orcamento.num_orcamento} cancelado com sucesso."})

@login_required
@require_POST
def alterar_status_orcamento(request):
    try:
        orc_id = request.POST.get("id")
        novo_status = request.POST.get("status")

        if not orc_id or not novo_status:
            return JsonResponse({"erro": "Dados inválidos"}, status=400)

        # Busca o orçamento
        orc = get_object_or_404(Orcamento, pk=orc_id)

        # Atualiza o status
        orc.status = novo_status
        orc.save(update_fields=["status"])

        return JsonResponse({"mensagem": "Status atualizado com sucesso!"})

    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)

@login_required
def imprimir_comprovante(request, id):
    orcamento = get_object_or_404(Orcamento, pk=id)
    # Pegando todas as formas de pagamento relacionadas
    formas_pgto = orcamento.formas_pgto.all()
    # Criando uma lista de formas convertidas para uso no template
    orcamento.formas_convertidas = [
        {
            "id": f.id,
            "descricao": f.formas_pgto.descricao if hasattr(f, 'formas_pgto') else str(f),
            "valor": float(f.valor)
        }
        for f in formas_pgto
    ]
    return render(request, 'orcamentos/comprovante.html', {
        'orcamento': orcamento,
        'formas_pgto': formas_pgto,
    })

@login_required
def imprimir_comp_a4(request, id):
    orcamento = get_object_or_404(Orcamento, pk=id)
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    larg_pag, alt_pag = A4
    pdfmetrics.registerFont(TTFont('Times', 'Allitec/static/fonts/Times.ttf'))
    pdfmetrics.registerFont(TTFont('Times Bold', 'Allitec/static/fonts/Times_Bold.ttf'))
    c.setTitle(f'RESUMO ORÇAMENTO - {orcamento.num_orcamento}')
    c.setFont("Times", 10)

    logo_path = os.path.join(settings.MEDIA_ROOT, str(orcamento.vinc_fil.logo))
    if os.path.exists(logo_path):
        with Image.open(logo_path) as img:
            if img.mode in ('RGBA', 'LA'):
                background = Image.new("RGB", img.size, (255, 255, 255))  # branco
                background.paste(img, mask=img.split()[3])  # usar alpha como máscara
                img = background
            else:
                img = img.convert("RGB")
            c.drawImage(ImageReader(img), (larg_pag - 8*cm)/2, alt_pag-4*cm, width=8*cm, height=3*cm)
    y = alt_pag - 3.5*cm
    filial = request.user.filial_user
    dados_filial = [
        filial.fantasia.upper(),
        filial.cnpj,
        f"{filial.endereco.upper()}, {filial.numero} - {filial.bairro_fil}",
        filial.cidade_fil,
        filial.tel
    ]
    y -= 20
    c.setFont("Times Bold", 12)
    for linha in dados_filial:
        c.drawCentredString(larg_pag/2, y, str(linha))
        y -= 14
    y -= 20
    c.line(40, y, larg_pag-40, y)
    y -= 16
    c.setFont("Times Bold", 14)
    c.drawCentredString(larg_pag/2, y, f"Resumo Orçamento {orcamento.num_orcamento} ({orcamento.situacao})")
    y -= 8
    c.line(40, y, larg_pag-40, y)
    y -= 20
    col_1 = [
        ("Nº Orçamento:", orcamento.num_orcamento), ("Dt. Emissão:", orcamento.dt_emi.strftime("%d/%m/%Y")),
        ("Solicitante:", orcamento.nome_solicitante), ("Razão Social:", orcamento.cli.razao_social),
        ("Cliente:", f"{orcamento.cli.id} - {orcamento.nome_cli}"), ("Endereço:", f"{orcamento.cli.endereco}, Nº {orcamento.cli.numero}"),
        ("CPF/CNPJ:", orcamento.cli.cpf_cnpj),
    ]
    col_2 = [
        ("Bairro:", orcamento.cli.bairro), ("Cidade:", orcamento.cli.cidade), ("UF:", orcamento.cli.uf),
        ("E-mail:", orcamento.cli.email),
    ]
    c.setFont("Times Bold", 9)
    c.drawString(175, y, f"HORA: {orcamento.dt_emi.strftime('%H:%M')}")
    c.drawRightString(larg_pag-40, y, f"IMPRESSO: {request.user.first_name}")
    for label, valor in col_1:
        c.setFont("Times Bold", 9)
        c.drawString(40, y, label)
        c.setFont("Times", 9)
        c.drawString(110, y, str(valor))
        y -= 14
    for label, valor in col_2:
        c.setFont("Times Bold", 9)
        c.drawString(350, y + 56, label)
        c.setFont("Times", 9)
        c.drawString(400, y + 56, str(valor))
        y -= 14
    y += 40
    c.line(40, y, larg_pag-40, y)
    y -= 12
    c.setFont("Times Bold", 10)
    c.drawCentredString(larg_pag/2, y, "RESUMO DAS FORMAS DE PAGAMENTO")
    y -= 6
    c.line(40, y, larg_pag-40, y)
    formas_pgto = orcamento.formas_pgto.all()
    for i, f in enumerate(formas_pgto, 1):
        c.setFont("Times", 9)
        c.drawString(50, y-12, f"{i:03d}")
        c.drawString(100, y-12, f.formas_pgto.descricao)
        c.drawRightString(larg_pag-50, y-12, f"R$ {f.valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        y -= 14
    y -= 20
    totais = [
        ("SUBTOTAL", orcamento.subtotal),
        ("DESCONTO", orcamento.desconto),
        ("ACRÉSCIMO", orcamento.acrescimo),
        ("TOTAL", orcamento.total),
    ]
    c.setFont("Times Bold", 10)
    for label, valor in totais:
        c.drawRightString(larg_pag-50, y, f"{label}: R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        y -= 14
    if orcamento.obs_form_pgto:
        y -= 20
        c.setFont("Times Bold", 10)
        c.drawCentredString(larg_pag/2, y, "OBSERVAÇÕES")
        y -= 14
        style = ParagraphStyle(name="Justify", alignment=TA_JUSTIFY, fontName="Times", fontSize=9)
        Paragraph(orcamento.obs_form_pgto, style).wrapOn(c, larg_pag-100, 100)
        Paragraph(orcamento.obs_form_pgto, style).drawOn(c, 50, y-60)
        y -= 80
    if orcamento.vinc_fil.info_comp:
        y -= 20
        c.setFont("Times", 10)
        c.drawCentredString(larg_pag/2, y, orcamento.vinc_fil.info_comp)
    y -= 80
    c.line(larg_pag - 40, y, larg_pag - 240, y)  # Linha da direita
    c.line(40, y, 240, y)  # Linha da esquerda
    c.setFont("Times Bold", 10)
    c.drawCentredString(larg_pag - 140, y - 15, "Responsável")  # Ajuste o 'y' conforme necessário
    c.drawCentredString(140, y - 15, orcamento.nome_cli)
    c.showPage()
    c.save()
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="RESUMO ORÇAMENTO - {orcamento.num_orcamento}.pdf"'
    return response

from reportlab.lib.utils import simpleSplit

@login_required
def gerar_contrato_pdf(request, id):
    o = Orcamento.objects.get(pk=id)
    pdfmetrics.registerFont(TTFont('Times', 'Allitec/static/fonts/Times.ttf'))
    pdfmetrics.registerFont(TTFont('Times Bold', 'Allitec/static/fonts/Times_Bold.ttf'))
    # Dados do contrato (simulados)
    dados = {
        "contratante": f"{o.cli.fantasia}", "cnpj_contratante": f"{o.cli.cpf_cnpj}", "logradouro_contratante": f"{o.cli.endereco}", "bairro_contratante": f"{o.cli.bairro}",
        "cidade_contratante": f"{o.cli.cidade}", "largura": f"{o.larg}", "altura": f"{o.alt}", "cor": f"{o.cor}", "valor": f"{o.total}",
        "cnpj_filial": f"{o.vinc_fil.cnpj}", "ie_filial": f"{o.vinc_fil.ie}", "endereco_filial": f"{o.vinc_fil.endereco}, Nº {o.vinc_fil.numero} - {o.vinc_fil.bairro_fil}",
        "cidade_filial": f"{o.vinc_fil.cidade_fil}", "cep_filial": f"{o.vinc_fil.cep}", "telefone_filial": f"{o.vinc_fil.tel}",
        "banco": f"{o.vinc_fil.banco_fil.cod_banco} - {o.vinc_fil.banco_fil.nome_banco}", "pix": f"{o.vinc_fil.chave_pix}",
        "nome_filial": f"{o.vinc_fil.razao_social}", "fantasia": f"{o.vinc_fil.fantasia.upper()}",
        "beneficiario": f"{o.vinc_fil.beneficiario}", "nome_dono": f"{o.vinc_fil.fantasia.upper()}"
    }
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    larg_pag, alt_pag = A4
    y = alt_pag - 80  # Margem inicial do topo
    p.setTitle(f'CONTRATO PORTA ENROLAR - {o.cli}')
    logo_path = os.path.join(settings.MEDIA_ROOT, str(o.vinc_fil.logo))
    # Abrir a imagem da logo
    if os.path.exists(logo_path):
        with Image.open(logo_path) as img:
            if img.mode in ('RGBA', 'LA'):
                background = Image.new("RGB", img.size, (255, 255, 255))  # branco
                background.paste(img, mask=img.split()[3])  # usar alpha como máscara
                img = background
            else:
                img = img.convert("RGB")
            p.drawImage(ImageReader(img), (larg_pag - 8*cm)/2, alt_pag-4*cm, width=8*cm, height=3*cm)
    y -= 30
    def write_line(text, font_size=12, gap=14, bold=False):
        nonlocal y
        # Define a fonte
        font_name = "Times Bold" if bold else "Times"
        p.setFont(font_name, font_size)

        # Define a largura máxima do texto (ajuste conforme suas margens)
        max_width = larg_pag - 60  # margem direita (página - margens esquerda/direita)

        # Quebra o texto automaticamente conforme o limite de largura
        lines = simpleSplit(text, font_name, font_size, max_width)

        # Escreve cada linha no PDF
        for line in lines:
            p.drawString(30, y, line)
            y -= gap
    def write_multiline(text, font_size=12, gap=14, bold=False):
        nonlocal y
        if bold:
            p.setFont("Times Bold", font_size)
        else:
            p.setFont("Times", font_size)
        # Quebrar o texto em palavras
        palavras = text.split(' ')
        linha = ""
        for palavra in palavras:
            # Adicionar a palavra à linha atual
            nova_linha = linha + palavra + ' '
            # Verificar se a nova linha cabe na largura
            if p.stringWidth(nova_linha, "Times Bold" if bold else "Times", font_size) < (larg_pag - 50):  # 60 é a margem
                linha = nova_linha
            else:
                # Escrever a linha atual e começar uma nova
                p.drawString(30, y, linha)
                y -= gap
                linha = palavra + ' '
        # Escrever a última linha se houver
        if linha:
            p.drawString(30, y, linha)
            y -= gap
    # Título
    y -= 15
    p.setFont("Times Bold", 16)
    p.drawCentredString(larg_pag / 2, y, "CONTRATO")
    y -= 30
    # Seções do contrato
    write_line(f"CONTRATANTE: {dados['contratante']}", bold=True)
    if o.cli.pessoa == "Jurídica":
        write_line(f"Sociedade Empresária, escrita no CNPJ sob o número: {dados['cnpj_contratante']}, com sede no logradouro: {dados['logradouro_contratante']}, Bairro: {dados['bairro_contratante']} - {dados['cidade_contratante']}")
    else:
        write_line(f"Pessoa Física, escrita no CPF sob o número: {dados['cnpj_contratante']}, com sede no logradouro: {dados['logradouro_contratante']}, Bairro: {dados['bairro_contratante']} - {dados['cidade_contratante']}")
    y -= 10
    write_line(f"CONTRATADA: {dados['nome_filial']}", bold=True)
    write_line(f"Sociedade Empresária, escrita no CNPJ sob o número: {dados['cnpj_filial']}, Inscrição Estadual: {dados['ie_filial']}, Endereço: {dados['endereco_filial']}, {dados['cidade_filial']}, CEP: {dados['cep_filial']}, Telefone: {dados['telefone_filial']}")

    y -= 10
    write_line("CLÁUSULA PRIMEIRA - DO OBJETO:", bold=True)
    def draw_circle(p, color, x, y, radius=10):
        p.setFillColor(color)
        p.circle(x, y, radius, stroke=0, fill=1)
    # Dentro da função gerar_contrato_pdf
    if o.pintura == 'Não':
        texto = f"Este CONTRATO é referente à Venda e instalação de uma porta de aço automatizada, medindo {dados['largura']}m x {dados['altura']}m, sem pintura."
    else:
        texto = f"Este CONTRATO é referente à Venda e instalação de uma porta de aço automatizada, medindo {dados['largura']}m x {dados['altura']}m, cor da lâmina: {dados['cor']}."
        # Desenhar o círculo da cor
        cores = {
            'Preto': 'black', 'Branco': 'white', 'Amarelo': 'yellow',
            'Vermelho': 'red', 'Roxo Açaí': '#6f2c91', 'Azul Pepsi': '#0051ff',
            'Azul Claro': '#a3c1e0', 'Cinza Claro': '#d3d3d3', 'Cinza Grafite': '#7e7e7e', 'Verde': 'green'
        }
        cor = cores.get(dados['cor'], 'black')
        # Desenhar o círculo
        draw_circle(p, cor, 180, y - 15)  # Chamada correta
    # Restaurar a cor do texto
    p.setFillColor('black')  # Defina a cor padrão do texto
    write_multiline(texto, bold=False)
    y -= 10
    write_line(f"Valor: R$ {dados['valor']}")
    y -= 10
    write_line("CLÁUSULA SEGUNDA - DO VALOR", bold=True)
    texto ="O COMPRADOR pagará ao VENDEDOR pela compra e instalação do objeto deste contrato, os pagamentos serão realizados ao termino da instalação da porta."
    write_multiline(texto, bold=False)
    write_line("Dados Bancários para pagamento (em caso de PIX):", bold=True)
    write_line(f"Banco: {dados['banco']}, Nome: {dados['beneficiario']}, Chave Pix: {dados['pix']}")
    y -= 10
    write_line("CLÁUSULA TERCEIRA - OBRIGAÇÕES", bold=True)
    write_line("A seguir, constam as obrigações de ambas as partes:")
    write_line("• A CONTRATADA deve iniciar a Instalação em até 15 dias após assinatura (FRETE INCLUSO).")
    write_line("• A CONTRATADA dispõe de 1 ano de assistência técnica gratuita (exceto mau uso).")
    write_line("• A CONTRATANTE deve prover ponto de energia 220V para funcionamento do motor.")
    y -= 10
    write_line("Parágrafo Único", bold=True)
    texto = "A gratuidade não cobre em Caso de ACIDENTE ou MAU USO: será cobrado deslocamento, mão de obra, estadias e peças caso for necessário."
    write_multiline(texto, bold=False)
    y -= 10
    write_line("CLÁUSULA QUARTA - DA MULTA:", bold=True)
    texto = "Em caso de inadimplência ou não pagamento na data acertada no presente contrato, resultará em multa de 2% (dois por cento) sobre o valor vencido + juros moratórios de 1% (um por cento) ao mês."
    write_multiline(texto, bold=False)
    y -= 10
    write_line("CLÁUSULA QUINTA - DA VIGÊNCIA:", bold=True)
    write_line("Este CONTRATO será válido a partir da assinatura ou aceite por e-mail entre as partes.")
    y -= 20
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    data_str = o.dt_emi
    data_formatada = data_str.strftime('%d de %B de %Y').upper()
    write_line(f"Local e data: {o.vinc_fil.cidade_fil.nome_cidade}, {data_formatada}", gap=30)
    y -= 10
    # Assinaturas
    p.drawString(40, y, "______________________________________")
    p.drawString(300, y, "______________________________________")
    y -= 30
    p.setFont("Times Bold", 12)
    larg_txt = p.stringWidth(dados['nome_dono'])
    pos_x = (larg_pag - larg_txt) / 5
    p.drawString(pos_x, y, dados['nome_dono'])
    larg_txt = p.stringWidth(dados['contratante'])
    pos_x = (larg_pag - larg_txt) / 1.40
    p.drawString(pos_x, y, dados['contratante'])
    y -= 40
    p.setFont("Times Bold", 9)
    p.drawCentredString(larg_pag / 2, y, f"{dados['nome_filial']} – CNPJ: {dados['cnpj_filial']} – I.E: {dados['ie_filial']}")
    y -= 12
    p.drawCentredString(larg_pag / 2, y, f"{dados['endereco_filial']} – {dados['cidade_filial']} – CEP: {dados['cep_filial']}")
    y -= 12
    p.drawCentredString(larg_pag / 2, y, f"Telefone: {dados['telefone_filial']}")
    # Finalizar
    p.showPage()
    p.save()
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')

@login_required
def pdf_contrato_v2(request, id):
    """Gera o PDF da proposta comercial (dinâmico, baseado no orçamento)."""
    o = Orcamento.objects.get(pk=id)

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    larg_pag, alt_pag = A4
    y = alt_pag - 70

    # --- Fontes ---
    pdfmetrics.registerFont(TTFont('Times', 'Allitec/static/fonts/Times.ttf'))
    pdfmetrics.registerFont(TTFont('Times Bold', 'Allitec/static/fonts/Times_Bold.ttf'))
    pdfmetrics.registerFont(TTFont('Times Bold Italic', 'Allitec/static/fonts/Times-Bold-Italic.ttf'))

    p.setTitle(f"Proposta Comercial - {o.num_orcamento}")

    # --- Logo ---
    logo_path = os.path.join(settings.MEDIA_ROOT, str(o.vinc_fil.logo))
    if os.path.exists(logo_path):
        with Image.open(logo_path) as img:
            if img.mode in ('RGBA', 'LA'):
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            p.drawImage(ImageReader(img), (larg_pag - 6*cm)/100, alt_pag-3*cm, width=6*cm, height=2.25*cm)
    y -= 20

    # --- Funções auxiliares ---
    def write_line(text, font_size=12, gap=14, bold=False):
        nonlocal y
        font = "Times Bold" if bold else "Helvetica"
        p.setFont(font, font_size)
        lines = simpleSplit(text, font, font_size, larg_pag - 50)
        for line in lines:
            p.drawString(30, y, line)
            y -= gap

    def write_multiline(text, font_size=12, gap=14, bold=False):
        nonlocal y
        font = "Times Bold" if bold else "Times"
        p.setFont(font, font_size)
        lines = simpleSplit(text, font, font_size, larg_pag - 60)
        for line in lines:
            p.drawString(30, y, line)
            y -= gap

    # --- Cabeçalho ---
    p.setFont("Times Bold", 16)
    p.drawString(40, y, "Proposta Comercial")
    y -= 20
    p.setFont("Times Bold Italic", 14)
    # Texto centralizado
    texto = "Instalação de Porta de Enrolar Automática"
    p.drawCentredString(larg_pag / 2, y, texto)

    # Linha abaixo do texto
    largura_texto = p.stringWidth(texto, "Helvetica", 12)  # Fonte e tamanho devem ser iguais ao do texto
    x_inicio = (larg_pag - largura_texto) / 2
    x_fim = x_inicio + largura_texto
    p.line(x_inicio - 6, y - 2, x_fim + 6, y - 2)  # linha 2 pontos abaixo do texto

    y -= 40
    p.setFont("Helvetica", 12)
    # --- Corpo ---
    write_line(f"A {o.fantasia_emp}, apresenta a seguinte proposta para fornecimento e instalação de porta de enrolar automática:", bold=False)
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    p.drawString(30, y, "✔ Descrição do Serviço:")
    p.setFont("Helvetica", 12)
    y -= 20
    p.drawString(40, y, "• Fornecimento de porta de enrolar automática sob medida;")
    y -= 15
    p.drawString(40, y, "• Estrutura em aço galvanizado com pintura eletrostática;")
    y -= 15
    p.drawString(40, y, "• Motor automatizador com 2 controles remoto;")
    y -= 15
    p.drawString(40, y, "• Instalação completa e testes de funcionamento.")
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    p.drawString(30, y, "✔ Diferenciais:")
    p.setFont("Helvetica", 12)
    y -= 20
    p.drawString(40, y, "• Profissionais qualificados;")
    y -= 15
    p.drawString(40, y, "• Equipamentos de alta durabilidade;")
    y -= 15
    p.drawString(40, y, "• Garantia de 12 meses;")
    y -= 15
    p.drawString(40, y, "• Suporte técnico LOCAL e especializado.")
    y -= 20

    # --- Valor e condições ---
    p.setFont("Helvetica-Bold", 12)
    texto_bold = "✔ Valor Estimado:"
    p.drawString(30, y, texto_bold)

    largura_titulo = p.stringWidth(texto_bold, "Helvetica-Bold", 12)
    p.setFont("Helvetica", 12)
    p.drawString(30 + largura_titulo + 5, y, f"R$ {o.total:,.2f}, referente à instalação de Porta Automática com medida de {o.alt}mt")
    y -= 15
    tem_portinhola = OrcamentoAdicional.objects.filter(
        orcamento=o,
        produto__desc_prod__iexact="PORTINHOLA",
        quantidade__gte=1.00
    ).exists()

    # Agora usa essa verificação junto com a pintura:
    if o.pintura == "Sim" and not tem_portinhola:
        p.drawString(30, y, f"de Altura e {o.larg}mt de Largura, com Pintura e sem Portinhola.")
    elif o.pintura == "Sim" and tem_portinhola:
        p.drawString(30, y, f"de Altura e {o.larg}mt de Largura, com Pintura e com Portinhola.")
    elif o.pintura != "Sim" and tem_portinhola:
        p.drawString(30, y, f"de Altura e {o.larg}mt de Largura, sem Pintura e com Portinhola.")
    else:
        p.drawString(30, y, f"de Altura e {o.larg}mt de Largura, sem Pintura e sem Portinhola.")
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    texto_bold = "✔ Forma de Pagamento:"
    p.drawString(30, y, texto_bold)

    largura_titulo = p.stringWidth(texto_bold, "Helvetica-Bold", 12)
    p.setFont("Helvetica", 12)
    p.drawString(30 + largura_titulo + 5, y, "50% no ato do fechamento e valor restante ao finalizar a instalação.")
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    texto_bold = "✔ Prazo de Instalação:"
    p.drawString(30, y, texto_bold)

    largura_titulo = p.stringWidth(texto_bold, "Helvetica-Bold", 12)
    p.setFont("Helvetica", 12)
    p.drawString(30 + largura_titulo + 5, y, "Até 20 dias úteis após a aprovação e pagamento, podendo variar de acordo")
    y -= 15
    p.drawString(30, y, "com estrutura do local de instalação.")
    y -= 25
    p.drawString(30, y, "Qualquer dúvida ou necessidade de ajuste, estamos à disposição!")
    y -= 40

    # --- Rodapé ---
    p.setFont("Helvetica-Bold", 12)
    p.drawString(30, y, f"{o.vinc_fil.info_comp}")
    y -= 30
    p.drawImage("Allitec/static/img/telefone.png", 30, y, width=15, height=15)
    p.drawString(50, y + 4, f"{o.vinc_fil.tel}")
    y -= 20
    p.drawImage("Allitec/static/img/email.png", 30, y, width=15, height=15)
    p.drawString(50, y + 4, f"{o.vinc_fil.email}")
    y -= 20
    p.drawImage("Allitec/static/img/local.png", 30, y, width=15, height=15)
    p.drawString(50, y + 4, "Atendemos em todo estado do Pará!")
    y -= 20
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    data_formatada = o.dt_emi.strftime('%d de %B de %Y').upper()
    p.drawString(30, y, f"{o.vinc_fil.cidade_fil} - {o.vinc_fil.uf}, {data_formatada}.")

    y -= 100
    p.line(100, y, larg_pag - 100, y)
    y -= 15
    p.drawCentredString(larg_pag / 2, y, f"{o.cli}")

    # --- Finalizar ---
    p.showPage()
    p.save()
    buffer.seek(0)

    return HttpResponse(buffer, content_type='application/pdf')

# @login_required
# def pdf_orcamento(request, id):
#     pdfmetrics.registerFont(TTFont('Segoe UI Bold', 'Allitec/static/fonts/segoe-ui-bold.ttf'))
#     pdfmetrics.registerFont(TTFont('Segoe UI', 'Allitec/static/fonts/Segoe UI.ttf'))
#     pdfmetrics.registerFont(TTFont('Arial-Narrow-Bold', 'Allitec/static/fonts/arialnarrow_bold.ttf'))
#     pdfmetrics.registerFont(TTFont('Times', 'Allitec/static/fonts/Times.ttf'))
#     pdfmetrics.registerFont(TTFont('Times Bold', 'Allitec/static/fonts/Times_Bold.ttf'))
#     o = Orcamento.objects.get(pk=id)
#     buffer = BytesIO()
#     c = canvas.Canvas(buffer, pagesize=A4)
#     larg_pag, alt_pag = A4
#     alt_pag += 40
#     logo_path = os.path.join(settings.MEDIA_ROOT, str(o.vinc_emp.logo))
#     if os.path.exists(logo_path):
#         with Image.open(logo_path) as img:
#             if img.mode in ('RGBA', 'LA'):
#                 background = Image.new("RGB", img.size, (255, 255, 255))  # branco
#                 background.paste(img, mask=img.split()[3])  # usar alpha como máscara
#                 img = background
#             else: img = img.convert("RGB")
#             c.drawImage(ImageReader(img), (larg_pag - 4*cm)/100, alt_pag-2*cm - 70, width=4*cm, height=1.5*cm)
#     c.setTitle(f'ORÇAMENTO PORTA ENROLAR - {o.nome_cli}')
#     c.setFont('Times Bold', 12)
#     larg_txt1 = c.stringWidth(f'ORÇAMENTO - {o.fantasia_emp}')
#     pos_x1 = (larg_pag - larg_txt1) / 3.5
#     yellow = colors.yellow
#     black = colors.black
#     gray = colors.gray
#     c.setFillColor(yellow)  # Define cor de preenchimento amarelo
#     c.rect(115,alt_pag - 100,larg_pag - 185 - 140,40,fill=1,stroke=0)
#     c.setFillColor(black)  # Muda cor de texto de volta para preto
#     c.drawString(pos_x1, alt_pag - 85, f'ORÇAMENTO - {o.fantasia_emp}')
#     c.setStrokeColor(black)  # Define cor da linha como preta
#     c.line(115, alt_pag - 60, larg_pag - 20, alt_pag - 60)
#     c.line(115, alt_pag - 59.5, 115, alt_pag - 99.5)
#     c.line(115, alt_pag - 100, larg_pag - 20, alt_pag - 100)
#     c.setFillColor(gray)  # Define cor de preenchimento amarelo
#     c.rect(385,alt_pag - 160,larg_pag - 140 - 365,100,fill=1,stroke=0 )
#     c.setFillColor(black)
#     c.setFont('Times Bold', 10)
#     c.drawString(390, alt_pag - 85, 'DT. EMISSÃO')
#     c.drawString(390, alt_pag - 115, 'Nº ORÇAMENTO')
#     c.drawString(390, alt_pag - 135, 'DT. ENTREGA')
#     c.drawString(390, alt_pag - 155, 'SOLICITANTE')
#     c.setFont('Times', 10)
#     c.drawString(480, alt_pag - 85, o.dt_emi.strftime('%d/%m/%Y'))
#     c.drawString(480, alt_pag - 115, f'{o.num_orcamento}')
#     if o.dt_ent: c.drawString(480, alt_pag - 135, o.dt_ent.strftime('%d/%m/%Y'))
#     else: c.drawString(480, alt_pag - 135, '')
#     c.setFont('Times Bold', 8)
#     c.drawString(120, alt_pag - 115, f'CNPJ: {o.vinc_emp.cnpj} | FONE {o.vinc_emp.tel}')
#     c.drawString(120, alt_pag - 135, f'END: {o.vinc_emp.endereco}, Nº: {o.vinc_emp.numero} BAIRRO: {o.vinc_emp.bairro_fil}')
#     c.drawString(120, alt_pag - 155, f'CIDADE: {o.vinc_emp.cidade_fil} | UF: {o.vinc_emp.uf} | CEP: {o.vinc_emp.cep}')
#     c.setFont('Times', 10)
#     c.drawString(480, alt_pag - 155, f'{o.nome_solicitante}')
#     c.line(250, alt_pag - 60, larg_pag - 20, alt_pag - 60)
#     c.line(larg_pag - 210, alt_pag - 59.5, larg_pag - 210, alt_pag - 160.5)
#     c.line(larg_pag - 20, alt_pag - 59.5, larg_pag - 20, alt_pag - 160.5)
#     c.line(250, alt_pag - 100, larg_pag - 20, alt_pag - 100)
#     c.line(300, alt_pag - 60, larg_pag - 20, alt_pag - 60)
#     c.line(larg_pag - 120, alt_pag - 59.5, larg_pag - 120, alt_pag - 160.5)
#     c.line(300, alt_pag - 100, larg_pag - 20, alt_pag - 100)
#     c.line(115, alt_pag - 99, 115, alt_pag - 160.5)
#     c.line(115, alt_pag - 120, larg_pag - 20, alt_pag - 120)
#     c.line(115, alt_pag - 140, larg_pag - 20, alt_pag - 140)
#     c.line(115, alt_pag - 160, larg_pag - 20, alt_pag - 160)
#     c.setFillColor(gray)  # Define cor de preenchimento amarelo
#     c.rect(15,alt_pag - 280,larg_pag - 140 - 390,100,fill=1, stroke=0)
#     c.rect(295,alt_pag - 280,larg_pag - 140 - 395,60,fill=1,stroke=0)
#     c.rect(495, alt_pag - 280, larg_pag - 140 - 433, 40, fill=1, stroke=0)
#     c.rect(15, alt_pag - 333, larg_pag - 20 - 15, 13, fill=1, stroke=0)
#     c.rect(15, alt_pag - 411, larg_pag - 20 - 15, 13, fill=1, stroke=0)
#     c.rect(15, alt_pag - 437, larg_pag - 20 - 15, 13, fill=1, stroke=0)
#     c.rect(15, alt_pag - 566.5, larg_pag - 20 - 15, 13, fill=1, stroke=0)
#     c.rect(15, alt_pag - 671, larg_pag - 20 - 15, 13, fill=1, stroke=0)
#     c.rect(15, alt_pag - 761.5, larg_pag - 20 - 15, 13, fill=1, stroke=0)
#     c.setFillColor(yellow)
#     c.rect(15, alt_pag - 345.5, larg_pag - 20 - 15, 13, fill=1, stroke=0)
#     cor_subtotal = colors.HexColor("#3CB371")
#     cor_desconto = colors.HexColor("#20B2AA")
#     cor_acrescimo = colors.HexColor("#F08080")
#     cor_total = colors.HexColor("#32CD32")
#     c.rect(15, alt_pag - 684.5, larg_pag - 20 - 190, 13, fill=1, stroke=0)
#     c.setFillColor(cor_subtotal)
#     c.rect(400, alt_pag - 684.5, larg_pag - 20 - 495, 13, fill=1, stroke=0)
#     c.setFillColor(cor_desconto)
#     c.rect(400, alt_pag - 696, larg_pag - 20 - 495, 12, fill=1, stroke=0)
#     c.setFillColor(cor_acrescimo)
#     c.rect(400, alt_pag - 709, larg_pag - 20 - 495, 13, fill=1, stroke=0)
#     c.setFillColor(cor_total)
#     c.rect(400, alt_pag - 722, larg_pag - 20 - 495, 13, fill=1, stroke=0)
#     c.setFillColor(black)
#     c.line(15, alt_pag - 179.5, 15, alt_pag - 300.5)
#     c.line(larg_pag - 20, alt_pag - 179.5, larg_pag - 20, alt_pag - 300.5)
#     c.line(15, alt_pag - 180, larg_pag - 20, alt_pag - 180)
#     c.line(15, alt_pag - 200, larg_pag - 20, alt_pag - 200)
#     c.line(15, alt_pag - 220, larg_pag - 20, alt_pag - 220)
#     c.line(15, alt_pag - 240, larg_pag - 20, alt_pag - 240)
#     c.line(15, alt_pag - 260, larg_pag - 20, alt_pag - 260)
#     c.line(15, alt_pag - 280, larg_pag - 20, alt_pag - 280)
#     c.line(15, alt_pag - 300, larg_pag - 20, alt_pag - 300)
#     c.line(80, alt_pag - 179.5, 80, alt_pag - 280.5)
#     c.line(larg_pag - 300, alt_pag - 219.5, larg_pag - 300, alt_pag - 280.5)
#     c.line(larg_pag - 240, alt_pag - 219.5, larg_pag - 240, alt_pag - 280.5)
#     c.line(larg_pag - 100, alt_pag - 239.5, larg_pag - 100, alt_pag - 280.5)
#     c.line(larg_pag - 78, alt_pag - 239.5, larg_pag - 78, alt_pag - 280.5)
#     c.setFont('Times Bold', 10)
#     c.drawString(20, alt_pag - 195, 'CLIENTE')
#     c.drawString(20, alt_pag - 215, 'CPF/CNPJ')
#     c.drawString(20, alt_pag - 235, 'E-MAIL')
#     c.drawString(20, alt_pag - 255, 'ENDEREÇO')
#     c.drawString(20, alt_pag - 275, 'CEP')
#     c.drawString(20, alt_pag - 295, 'OBSERVAÇÕES:')
#     c.drawImage('Allitec/static/img/whatsapp.png', 337, alt_pag - 238, width=12, height=14, mask='auto')
#     c.drawString(300, alt_pag - 235, 'FONE /')
#     c.drawString(300, alt_pag - 255, 'BAIRRO')
#     c.drawString(500, alt_pag - 255, 'Nº')
#     c.drawString(300, alt_pag - 275, 'CIDADE')
#     c.drawString(500, alt_pag - 275, 'UF')
#     c.line(larg_pag - 270, alt_pag - 199.5, larg_pag - 270, alt_pag - 219.5)
#     c.drawString(330, alt_pag - 215, 'RG/IE')
#     c.line(larg_pag - 210, alt_pag - 199.5, larg_pag - 210, alt_pag - 219.5)
#     c.setFont('Times', 10)
#     c.drawString(85, alt_pag - 195, f'{o.nome_cli}')
#     c.drawString(85, alt_pag - 215, f'{o.cli.cpf_cnpj}')
#     c.drawString(390, alt_pag - 215, f'{o.cli.ie}')
#     c.drawString(85, alt_pag - 235, f'{o.cli.email}')
#     c.drawString(360, alt_pag - 235, f'{o.cli.tel}')
#     c.drawString(85, alt_pag - 255, f'{o.cli.endereco}')
#     c.drawString(360, alt_pag - 255, f'{o.cli.bairro}')
#     c.drawString(525, alt_pag - 255, f'{o.cli.numero}')
#     c.drawString(85, alt_pag - 275, f'{o.cli.cep}')
#     c.drawString(100, alt_pag - 295, f'{o.obs_cli}')
#     c.drawString(360, alt_pag - 275, f'{o.cli.cidade}')
#     c.drawString(525, alt_pag - 275, f'{o.cli.uf}')
#     c.setFont('Times Bold', 10)
#     c.line(15, alt_pag - 320, larg_pag - 20, alt_pag - 320)
#     larg_txt = c.stringWidth('MEDIDAS')
#     pos_x = (larg_pag - larg_txt) / 2
#     c.drawString(pos_x, alt_pag - 330, 'MEDIDAS')
#     c.line(15, alt_pag - 333, larg_pag - 20, alt_pag - 333)
#     c.line(15, alt_pag - 346, larg_pag - 20, alt_pag - 346)
#     c.line(15, alt_pag - 359, larg_pag - 20, alt_pag - 359)
#     c.line(15, alt_pag - 319.5, 15, alt_pag - 814.5)
#     c.line(larg_pag - 20, alt_pag - 319.5, larg_pag - 20, alt_pag - 814.5)
#     c.line(60, alt_pag - 333.5, 60, alt_pag - 359.5)
#     c.line(140, alt_pag - 333.5, 140, alt_pag - 359.5)
#     c.line(280, alt_pag - 333.5, 280, alt_pag - 359.5)
#     c.line(360, alt_pag - 333.5, 360, alt_pag - 359.5)
#     c.line(440, alt_pag - 333.5, 440, alt_pag - 359.5)
#     c.line(500, alt_pag - 333.5, 500, alt_pag - 359.5)
#     c.drawString(26, alt_pag - 343.5, 'QTD          TIPO LÂM.                    TIPO DO VÃO                     LARGURA             ALTURA           PINTURA             COR')
#     c.setFont('Times', 10)
#     c.drawString(20, alt_pag - 356, f'{o.qtd}')
#     c.drawString(65, alt_pag - 356, f'{o.tp_lamina}')
#     c.drawString(145, alt_pag - 356, f'{o.tp_vao}')
#     c.drawString(285, alt_pag - 356, f'{o.larg}')
#     c.drawString(365, alt_pag - 356, f'{o.alt}')
#     c.drawString(445, alt_pag - 356, f'{o.pintura}')
#     if o.pintura == 'Sim': c.drawString(505, alt_pag - 356, f'{o.cor}')
#     else: c.drawString(535, alt_pag - 356, '-')
#     c.line(15, alt_pag - 372, larg_pag - 20, alt_pag - 372)
#     c.line(15, alt_pag - 385, larg_pag - 20, alt_pag - 385)
#     c.setFont('Times Bold', 10)
#     c.line(90, alt_pag - 371.5, 90, alt_pag - 398.5)
#     c.line(140, alt_pag - 371.5, 140, alt_pag - 398.5)
#     c.line(240, alt_pag - 371.5, 240, alt_pag - 398.5)
#     c.line(340, alt_pag - 371.5, 340, alt_pag - 398.5)
#     c.line(440, alt_pag - 371.5, 440, alt_pag - 398.5)
#     c.line(500, alt_pag - 371.5, 500, alt_pag - 398.5)
#     c.drawString(20, alt_pag - 382.5, 'FATOR PESO       PESO           EIXO/MOTOR             LARG. CORTE              ALT. CORTE              ROLO                   M²')
#     c.setFont('Times', 10)
#     c.drawString(20, alt_pag - 395, f'{o.fator_peso.replace(".", ",")}')
#     c.drawString(95, alt_pag - 395, f'{o.peso}')
#     c.drawString(145, alt_pag - 395, f'{o.eixo_motor}')
#     c.drawString(245, alt_pag - 395, f'{o.larg_corte.replace(".", ",")}')
#     c.drawString(345, alt_pag - 395, f'{o.alt_corte}')
#     c.drawString(445, alt_pag - 395, f'{o.rolo}')
#     c.drawString(505, alt_pag - 395, f'{o.m2.replace(".", ",")}')
#     c.line(15, alt_pag - 398, larg_pag - 20, alt_pag - 398)
#     c.setFont('Times Bold', 10)
#     larg_txt = c.stringWidth('ITENS DO ORÇAMENTO')
#     pos_x = (larg_pag - larg_txt) / 2
#     c.drawString(pos_x, alt_pag - 408, 'ITENS DO ORÇAMENTO')
#     c.line(15, alt_pag - 411, larg_pag - 20, alt_pag - 411)
#     c.line(85, alt_pag - 423.5, 85, alt_pag - 553.5)
#     c.line(240, alt_pag - 423.5, 240, alt_pag - 553.5)
#     c.line(330, alt_pag - 423.5, 330, alt_pag - 553.5)
#     c.line(393, alt_pag - 423.5, 393, alt_pag - 553.5)
#     c.line(470, alt_pag - 423.5, 470, alt_pag - 553.5)
#     c.drawString(20, alt_pag - 434, ' CÓD. PROD.                DESC. PRODUTO                       UNIDADE            VL. UNIT.     QUANTIDADE            VL. TOTAL')
#     c.line(15, alt_pag - 424, larg_pag - 20, alt_pag - 424)
#     c.line(15, alt_pag - 437, larg_pag - 20, alt_pag - 437)
#     c.setFont('Times', 10)
#     alt_produto = alt_pag - 447  # primeira linha de produto
#     for p in o.produtos.all():
#         prod = p.produto  # pega o Produto relacionado
#         tabela = prod.produtotabela_set.first()
#         c.drawString(20, alt_produto, f"{prod.id}")
#         c.drawString(90, alt_produto, f"{prod.desc_prod}")
#         c.drawString(245, alt_produto, f"{prod.unidProd.nome_unidade}")
#         valor_str = str(tabela.vl_prod) # remove milhar e converte vírgula em ponto
#         valor_decimal = Decimal(valor_str)
#         c.drawString(335, alt_produto, f"R$ {valor_decimal:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
#         c.drawString(398, alt_produto, f"{p.quantidade}".replace(".", ","))
#         c.drawString(475, alt_produto, f"R$ {p.subtotalVenda1:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
#         c.line(15, alt_produto - 2, larg_pag - 20, alt_produto - 2)
#         alt_produto -= 13
#     c.setFont('Times Bold', 10)
#     larg_txt = c.stringWidth('ADICIONAIS')
#     pos_x = (larg_pag - larg_txt) / 2
#     c.drawString(pos_x, alt_pag - 563, 'ADICIONAIS')
#     c.line(85, alt_pag - 566.5, 85, alt_pag - 644.5)
#     c.line(240, alt_pag - 566.5, 240, alt_pag - 644.5)
#     c.line(330, alt_pag - 566.5, 330, alt_pag - 644.5)
#     c.line(393, alt_pag - 566.5, 393, alt_pag - 644.5)
#     c.line(470, alt_pag - 566.5, 470, alt_pag - 644.5)
#     c.setFont('Times', 10)
#     alt_adicional = alt_pag - 577  # primeira linha de produto
#     for a in o.adicionais.all():
#         adc = a.produto  # pega o Produto relacionado
#         tabela1 = adc.produtotabela_set.first()
#         c.drawString(20, alt_adicional, f"{adc.id}")
#         c.drawString(90, alt_adicional, f"{adc.desc_prod}")
#         c.drawString(245, alt_adicional, f"{adc.unidProd.nome_unidade}")
#         valor_str1 = str(tabela1.vl_prod) # remove milhar e converte vírgula em ponto
#         valor_decimal1 = Decimal(valor_str1)
#         c.drawString(335, alt_adicional, f"R$ {valor_decimal1:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
#         c.drawString(398, alt_adicional, f"{a.quantidade}".replace(".", ","))
#         c.drawString(475, alt_adicional, f"R$ {a.subtotalVenda2:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
#         c.line(15, alt_adicional - 2, larg_pag - 20, alt_adicional - 2)
#         alt_adicional -= 13
#     c.line(15, alt_pag - 567, larg_pag - 20, alt_pag - 567)
#     c.setFont('Times Bold', 10)
#     larg_txt = c.stringWidth('CONDIÇÕES DE PAGAMENTO')
#     pos_x = (larg_pag - larg_txt) / 2
#     c.drawString(pos_x, alt_pag - 668, 'CONDIÇÕES DE PAGAMENTO')
#     c.line(15, alt_pag - 658, larg_pag - 20, alt_pag - 658)
#     c.line(160, alt_pag - 670.5, 160, alt_pag - 736.5)
#     c.line(400, alt_pag - 670.5, 400, alt_pag - 736.5)
#     c.line(480, alt_pag - 670.5, 480, alt_pag - 736.5)
#     c.drawString(23, alt_pag - 682, 'FORMAS DE PAGAMENTO                                     OBSERVAÇÕES                                  SUBTOTAL')
#     c.drawString(405, alt_pag - 694, 'DESCONTO')
#     c.drawString(405, alt_pag - 707, 'ACRÉSCIMO')
#     c.drawString(405, alt_pag - 720, 'TOTAL')
#     c.line(400, alt_pag - 696, larg_pag - 20, alt_pag - 696)
#     c.line(400, alt_pag - 709, larg_pag - 20, alt_pag - 709)
#     c.line(400, alt_pag - 722, larg_pag - 20, alt_pag - 722)
#     c.line(15, alt_pag - 671, larg_pag - 20, alt_pag - 671)
#     c.setFont('Times', 10)
#     c.drawString(485, alt_pag - 682, "R$ " + f"{o.subtotal:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
#     str_desc = str(o.desconto)
#     c.drawString(485, alt_pag - 693.5, "R$ " + str_desc.replace('.', ','))
#     str_acres = str(o.acrescimo)
#     c.drawString(485, alt_pag - 706.5, "R$ " + str_acres.replace('.', ','))
#     c.drawString(485, alt_pag - 719.5, "R$ " + f"{o.total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
#     alt_forma = alt_pag - 694  # primeira linha de produto
#     for f in o.formas_pgto.all():
#         fp = f.formas_pgto  # pega o Produto relacionado
#         c.drawString(20, alt_forma, f"{fp.descricao}")
#         c.drawString(95, alt_forma, f"R$ {f.valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
#         c.line(15, alt_forma - 2, larg_pag - 435, alt_forma - 2)
#         alt_forma -= 13
#     c.line(15, alt_pag - 684, larg_pag - 20, alt_pag - 684)
#     c.setFont('Times Bold', 10)
#     larg_txt = c.stringWidth('ASSINATURAS')
#     pos_x = (larg_pag - larg_txt) / 2
#     c.drawString(pos_x, alt_pag - 759, 'ASSINATURAS')
#     larg_txt = c.stringWidth(f'{o.vinc_emp.razao_social}')
#     pos_x = (larg_pag - larg_txt) / 6.50
#     c.drawString(pos_x, alt_pag - 810, f'{o.vinc_emp.razao_social}')
#     larg_txt = c.stringWidth('CLIENTE')
#     pos_x = (larg_pag - larg_txt) / 1.25
#     c.drawString(pos_x, alt_pag - 810, 'CLIENTE')
#     c.line(15, alt_pag - 553, larg_pag - 20, alt_pag - 553)
#     c.line(15, alt_pag - 736, larg_pag - 20, alt_pag - 736)
#     c.line(15, alt_pag - 749, larg_pag - 20, alt_pag - 749)
#     c.line(15, alt_pag - 762, larg_pag - 20, alt_pag - 762)
#     c.line(30, alt_pag - 800, larg_pag - 360, alt_pag - 800)
#     c.line(360, alt_pag - 800, larg_pag - 30, alt_pag - 800)
#     c.line(15, alt_pag - 814, larg_pag - 20, alt_pag - 814)
#     style = ParagraphStyle(name='Justify', alignment=TA_JUSTIFY, fontName="Times", fontSize=6)
#     obs = o.obs_form_pgto or ''  # garante que não seja None
#     larg_max = larg_pag - 375
#     parag_obs = Paragraph(obs, style)
#     w, h = parag_obs.wrap(larg_max, alt_pag)
#     altura_linha = 7  # para fontSize 6, isso é razoável
#     num_linhas = max(1, round(h / altura_linha))
#     posicoes_y = {1: alt_pag - 710,2: alt_pag - 717,3: alt_pag - 724,4: alt_pag - 721,5: alt_pag - 728,}
#     pos_y = posicoes_y.get(num_linhas, alt_pag - 745)
#     parag_obs.drawOn(c, 165, pos_y)
#     style_rodape = ParagraphStyle(name='Justify', alignment=TA_JUSTIFY, fontName="Times Bold", fontSize=10)
#     rodape = o.vinc_emp.info_orcamento
#     larg_max = larg_pag - 30
#     parag_rodape = Paragraph(rodape, style_rodape)
#     w, h = parag_rodape.wrap(larg_max, alt_pag)
#     parag_rodape.drawOn(c, 15, alt_pag - 850)
#     alt_pag -= 20
#     c.setFont('Times Bold', 18)
#     c.save()
#     buffer.seek(0)
#     response = HttpResponse(buffer, content_type='application/pdf')
#     response['Content-Disposition'] = f'filename="ORÇAMENTO PORTA ENROLAR - {o.id}.pdf"'
#     return response

@login_required
def pdf_orcamento(request, id):
    pdfmetrics.registerFont(TTFont('Segoe UI Bold', 'Allitec/static/fonts/segoe-ui-bold.ttf'))
    pdfmetrics.registerFont(TTFont('Segoe UI', 'Allitec/static/fonts/Segoe UI.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Narrow-Bold', 'Allitec/static/fonts/arialnarrow_bold.ttf'))
    pdfmetrics.registerFont(TTFont('Times', 'Allitec/static/fonts/Times.ttf'))
    pdfmetrics.registerFont(TTFont('Times Bold', 'Allitec/static/fonts/Times_Bold.ttf'))

    o = Orcamento.objects.get(pk=id)
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    larg_pag, alt_pag = A4
    alt_pag += 40

    yellow = colors.yellow
    black = colors.black
    gray = colors.gray
    cor_subtotal = colors.HexColor("#3CB371")
    cor_desconto = colors.HexColor("#20B2AA")
    cor_acrescimo = colors.HexColor("#F08080")
    cor_total = colors.HexColor("#32CD32")

    logo_path = os.path.join(settings.MEDIA_ROOT, str(o.vinc_fil.logo))
    if os.path.exists(logo_path):
        try:
            with Image.open(logo_path) as img:
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                else:
                    img = img.convert("RGB")
                c.drawImage(ImageReader(img), (larg_pag - 3*cm)/100, alt_pag-1.75*cm - 70, width=3.5*cm, height=1.30*cm)
        except Exception:
            pass

    c.setTitle(f'ORÇAMENTO PORTA ENROLAR - {o.nome_cli}')
    c.setFont('Times Bold', 12)

    def draw_top_header():
        larg_txt1 = c.stringWidth(f'ORÇAMENTO - {o.fantasia_emp}')
        pos_x1 = (larg_pag - larg_txt1) / 3.5
        c.setFillColor(yellow)
        c.rect(115,alt_pag - 100,larg_pag - 185 - 140,40,fill=1,stroke=0)
        c.setFillColor(black)
        c.drawString(pos_x1, alt_pag - 85, f'ORÇAMENTO - {o.fantasia_emp}')
        c.setStrokeColor(black)
        c.line(115, alt_pag - 60, larg_pag - 20, alt_pag - 60)
        c.line(115, alt_pag - 59.5, 115, alt_pag - 99.5)
        c.line(115, alt_pag - 100, larg_pag - 20, alt_pag - 100)
        c.setFillColor(gray)
        c.rect(385,alt_pag - 160,larg_pag - 140 - 365,100,fill=1,stroke=0 )
        c.setFillColor(black)
        c.setFont('Times Bold', 10)
        c.drawString(390, alt_pag - 85, 'DT. EMISSÃO')
        c.drawString(390, alt_pag - 115, 'Nº ORÇAMENTO')
        c.drawString(390, alt_pag - 135, 'DT. ENTREGA')
        c.drawString(390, alt_pag - 155, 'SOLICITANTE')
        c.setFont('Times', 10)
        c.drawString(480, alt_pag - 85, o.dt_emi.strftime('%d/%m/%Y'))
        c.drawString(480, alt_pag - 115, f'{o.num_orcamento}')
        if o.dt_ent:
            c.drawString(480, alt_pag - 135, o.dt_ent.strftime('%d/%m/%Y'))
        else:
            c.drawString(480, alt_pag - 135, '')
        c.setFont('Times Bold', 8)
        c.drawString(120, alt_pag - 115, f'CNPJ: {o.vinc_fil.cnpj} | FONE {o.vinc_fil.tel}')
        c.drawString(120, alt_pag - 135, f'END: {o.vinc_fil.endereco}, Nº: {o.vinc_fil.numero} BAIRRO: {o.vinc_fil.bairro_fil}')
        c.drawString(120, alt_pag - 155, f'CIDADE: {o.vinc_fil.cidade_fil} | UF: {o.vinc_fil.uf} | CEP: {o.vinc_fil.cep}')
        c.setFont('Times', 10)
        c.drawString(480, alt_pag - 155, f'{o.nome_solicitante}')
        c.line(250, alt_pag - 60, larg_pag - 20, alt_pag - 60)
        c.line(larg_pag - 210, alt_pag - 59.5, larg_pag - 210, alt_pag - 160.5)
        c.line(larg_pag - 20, alt_pag - 59.5, larg_pag - 20, alt_pag - 160.5)
        c.line(250, alt_pag - 100, larg_pag - 20, alt_pag - 100)
        c.line(300, alt_pag - 60, larg_pag - 20, alt_pag - 60)
        c.line(larg_pag - 120, alt_pag - 59.5, larg_pag - 120, alt_pag - 160.5)
        c.line(300, alt_pag - 100, larg_pag - 20, alt_pag - 100)
        c.line(115, alt_pag - 99, 115, alt_pag - 160.5)
        c.line(115, alt_pag - 120, larg_pag - 20, alt_pag - 120)
        c.line(115, alt_pag - 140, larg_pag - 20, alt_pag - 140)
        c.line(115, alt_pag - 160, larg_pag - 20, alt_pag - 160)

    def draw_client_header():
        c.setFillColor(gray)
        c.rect(15,alt_pag - 280,larg_pag - 140 - 390,100,fill=1, stroke=0)
        c.rect(295,alt_pag - 280,larg_pag - 140 - 395,60,fill=1,stroke=0)
        c.rect(495, alt_pag - 280, larg_pag - 140 - 433, 40, fill=1, stroke=0)
        c.rect(15, alt_pag - 333, larg_pag - 20 - 15, 13, fill=1, stroke=0)
        c.rect(15, alt_pag - 411, larg_pag - 20 - 15, 13, fill=1, stroke=0)
        c.rect(15, alt_pag - 437, larg_pag - 20 - 15, 13, fill=1, stroke=0)
        c.rect(15, alt_pag - 566.5, larg_pag - 20 - 15, 13, fill=1, stroke=0)
        c.rect(15, alt_pag - 671, larg_pag - 20 - 15, 13, fill=1, stroke=0)
        c.rect(15, alt_pag - 761.5, larg_pag - 20 - 15, 13, fill=1, stroke=0)
        c.setFillColor(yellow)
        c.rect(15, alt_pag - 345.5, larg_pag - 20 - 15, 13, fill=1, stroke=0)
        c.setFillColor(black)
        c.line(15, alt_pag - 179.5, 15, alt_pag - 300.5)
        c.line(larg_pag - 20, alt_pag - 179.5, larg_pag - 20, alt_pag - 300.5)
        c.line(15, alt_pag - 180, larg_pag - 20, alt_pag - 180)
        c.line(15, alt_pag - 200, larg_pag - 20, alt_pag - 200)
        c.line(15, alt_pag - 220, larg_pag - 20, alt_pag - 220)
        c.line(15, alt_pag - 240, larg_pag - 20, alt_pag - 240)
        c.line(15, alt_pag - 260, larg_pag - 20, alt_pag - 260)
        c.line(15, alt_pag - 280, larg_pag - 20, alt_pag - 280)
        c.line(15, alt_pag - 300, larg_pag - 20, alt_pag - 300)
        c.line(80, alt_pag - 179.5, 80, alt_pag - 280.5)
        c.line(larg_pag - 300, alt_pag - 219.5, larg_pag - 300, alt_pag - 280.5)
        c.line(larg_pag - 240, alt_pag - 219.5, larg_pag - 240, alt_pag - 280.5)
        c.line(larg_pag - 100, alt_pag - 239.5, larg_pag - 100, alt_pag - 280.5)
        c.line(larg_pag - 78, alt_pag - 239.5, larg_pag - 78, alt_pag - 280.5)
        c.setFont('Times Bold', 10)
        c.drawString(20, alt_pag - 195, 'CLIENTE')
        c.drawString(20, alt_pag - 215, 'CPF/CNPJ')
        c.drawString(20, alt_pag - 235, 'E-MAIL')
        c.drawString(20, alt_pag - 255, 'ENDEREÇO')
        c.drawString(20, alt_pag - 275, 'CEP')
        c.drawString(20, alt_pag - 295, 'OBSERVAÇÕES:')
        try:
            c.drawImage('Allitec/static/img/whatsapp.png', 337, alt_pag - 238, width=12, height=14, mask='auto')
        except Exception:
            pass
        c.drawString(300, alt_pag - 235, 'FONE /')
        c.drawString(300, alt_pag - 255, 'BAIRRO')
        c.drawString(500, alt_pag - 255, 'Nº')
        c.drawString(300, alt_pag - 275, 'CIDADE')
        c.drawString(500, alt_pag - 275, 'UF')
        c.line(larg_pag - 270, alt_pag - 199.5, larg_pag - 270, alt_pag - 219.5)
        c.drawString(330, alt_pag - 215, 'RG/IE')
        c.line(larg_pag - 210, alt_pag - 199.5, larg_pag - 210, alt_pag - 219.5)
        c.setFont('Times', 10)
        c.drawString(85, alt_pag - 195, f'{o.nome_cli}')
        c.drawString(85, alt_pag - 215, f'{o.cli.cpf_cnpj}')
        c.drawString(390, alt_pag - 215, f'{o.cli.ie}')
        c.drawString(85, alt_pag - 235, f'{o.cli.email}')
        c.drawString(360, alt_pag - 235, f'{o.cli.tel}')
        c.drawString(85, alt_pag - 255, f'{o.cli.endereco}')
        c.drawString(360, alt_pag - 255, f'{o.cli.bairro}')
        c.drawString(525, alt_pag - 255, f'{o.cli.numero}')
        c.drawString(85, alt_pag - 275, f'{o.cli.cep}')
        c.drawString(100, alt_pag - 295, f'{o.obs_cli}')
        c.drawString(360, alt_pag - 275, f'{o.cli.cidade}')
        c.drawString(525, alt_pag - 275, f'{o.cli.uf}')
        c.setFont('Times Bold', 10)
        c.line(15, alt_pag - 320, larg_pag - 20, alt_pag - 320)
        larg_txt = c.stringWidth('MEDIDAS')
        pos_x = (larg_pag - larg_txt) / 2
        c.drawString(pos_x, alt_pag - 330, 'MEDIDAS')
        c.line(15, alt_pag - 333, larg_pag - 20, alt_pag - 333)
        c.line(15, alt_pag - 346, larg_pag - 20, alt_pag - 346)
        c.line(15, alt_pag - 359, larg_pag - 20, alt_pag - 359)
        c.line(15, alt_pag - 319.5, 15, alt_pag - 814.5)
        c.line(larg_pag - 20, alt_pag - 319.5, larg_pag - 20, alt_pag - 814.5)
        c.line(60, alt_pag - 333.5, 60, alt_pag - 359.5)
        c.line(140, alt_pag - 333.5, 140, alt_pag - 359.5)
        c.line(240, alt_pag - 333.5, 240, alt_pag - 359.5)
        c.line(300, alt_pag - 333.5, 300, alt_pag - 359.5)
        c.line(360, alt_pag - 333.5, 360, alt_pag - 359.5)
        c.line(440, alt_pag - 333.5, 440, alt_pag - 359.5)
        c.line(500, alt_pag - 333.5, 500, alt_pag - 359.5)
        c.drawString(26, alt_pag - 343.5, 'QTD          TIPO LÂM.            TIPO DO VÃO         QTD. LÂM.   LARGURA         ALTURA           PINTURA             COR')
        c.setFont('Times', 10)
        c.drawString(20, alt_pag - 356, f'{o.qtd}')
        c.drawString(65, alt_pag - 356, f'{o.tp_lamina}')
        c.drawString(145, alt_pag - 356, f'{o.tp_vao}')
        c.drawString(245, alt_pag - 356, f'{o.qtd_lam}')
        c.drawString(305, alt_pag - 356, f'{o.larg}')
        c.drawString(363, alt_pag - 356, f'{o.alt}')
        c.drawString(445, alt_pag - 356, f'{o.pintura}')
        if o.pintura == 'Sim':
            c.drawString(505, alt_pag - 356, f'{o.cor}')
        else:
            c.drawString(535, alt_pag - 356, '-')
        c.line(15, alt_pag - 372, larg_pag - 20, alt_pag - 372)
        c.line(15, alt_pag - 385, larg_pag - 20, alt_pag - 385)
        c.setFont('Times Bold', 10)
        c.line(90, alt_pag - 371.5, 90, alt_pag - 398.5)
        c.line(140, alt_pag - 371.5, 140, alt_pag - 398.5)
        c.line(240, alt_pag - 371.5, 240, alt_pag - 398.5)
        c.line(340, alt_pag - 371.5, 340, alt_pag - 398.5)
        c.line(440, alt_pag - 371.5, 440, alt_pag - 398.5)
        c.line(500, alt_pag - 371.5, 500, alt_pag - 398.5)
        c.drawString(20, alt_pag - 382.5, 'FATOR PESO       PESO           EIXO/MOTOR             LARG. CORTE              ALT. CORTE              ROLO                   M²')
        c.setFont('Times', 10)
        c.drawString(20, alt_pag - 395, f'{o.fator_peso.replace(".", ",")}')
        c.drawString(95, alt_pag - 395, f'{o.peso}')
        c.drawString(145, alt_pag - 395, f'{o.eixo_motor}')
        c.drawString(245, alt_pag - 395, f'{o.larg_corte.replace(".", ",")}')
        c.drawString(345, alt_pag - 395, f'{o.alt_corte}')
        c.drawString(445, alt_pag - 395, f'{o.rolo}')
        c.drawString(505, alt_pag - 395, f'{o.m2.replace(".", ",")}')
        c.line(15, alt_pag - 398, larg_pag - 20, alt_pag - 398)
        c.setFont('Times Bold', 10)
        larg_txt = c.stringWidth('ITENS DO ORÇAMENTO')
        pos_x = (larg_pag - larg_txt) / 2
        c.drawString(pos_x, alt_pag - 408, 'ITENS DO ORÇAMENTO')
        c.line(15, alt_pag - 411, larg_pag - 20, alt_pag - 411)
        c.line(85, alt_pag - 423.5, 85, alt_pag - 553.5)
        c.line(240, alt_pag - 423.5, 240, alt_pag - 553.5)
        c.line(330, alt_pag - 423.5, 330, alt_pag - 553.5)
        c.line(393, alt_pag - 423.5, 393, alt_pag - 553.5)
        c.line(470, alt_pag - 423.5, 470, alt_pag - 553.5)
        c.drawString(20, alt_pag - 434, ' CÓD. PROD.                DESC. PRODUTO                       UNIDADE            VL. UNIT.     QUANTIDADE            VL. TOTAL')
        c.line(15, alt_pag - 424, larg_pag - 20, alt_pag - 424)
        c.line(15, alt_pag - 437, larg_pag - 20, alt_pag - 437)
        alt_produto_init = alt_pag - 447
        alt_adicional_init = alt_pag - 577
        return alt_produto_init, alt_adicional_init

    draw_top_header()
    alt_produto, alt_adicional = draw_client_header()

    c.setFillColor(cor_subtotal)
    c.rect(400, alt_pag - 684.5, larg_pag - 20 - 495, 13, fill=1, stroke=0)
    c.setFillColor(cor_desconto)
    c.rect(400, alt_pag - 696, larg_pag - 20 - 495, 12, fill=1, stroke=0)
    c.setFillColor(cor_acrescimo)
    c.rect(400, alt_pag - 709, larg_pag - 20 - 495, 13, fill=1, stroke=0)
    c.setFillColor(cor_total)
    c.rect(400, alt_pag - 722, larg_pag - 20 - 495, 13, fill=1, stroke=0)

    c.setFont('Times', 10)
    linha_altura = 13
    max_por_pagina_prod = 9
    max_por_pagina_adic = 6

    produtos = list(o.produtos.all())
    adicionais = list(o.adicionais.all())

    c.setFillColor(black)

    prod_count = 0
    for p in produtos:
        prod = p.produto
        tabela = prod.produtotabela_set.first()
        if prod_count >= max_por_pagina_prod:
            c.showPage()
            draw_top_header()
            alt_produto, alt_adicional = draw_client_header()
            c.setFont('Times', 10)
            prod_count = 0
        c.drawString(20, alt_produto, f"{prod.id}")
        c.drawString(90, alt_produto, f"{prod.desc_prod}")
        c.drawString(245, alt_produto, f"{prod.unidProd.nome_unidade}")
        valor_str = str(tabela.vl_prod) if tabela else "0"
        valor_decimal = Decimal(valor_str)
        c.drawString(335, alt_produto, f"R$ {valor_decimal:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c.drawString(398, alt_produto, f"{p.quantidade}".replace(".", ","))
        c.drawString(475, alt_produto, f"R$ {p.subtotalVenda1:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c.line(15, alt_produto - 2, larg_pag - 20, alt_produto - 2)
        alt_produto -= linha_altura
        prod_count += 1

    espaço_para_header_e_linha = 40 + linha_altura
    y_titulo_adicionais = alt_pag - 563
    if alt_produto < (y_titulo_adicionais - espaço_para_header_e_linha):
        c.showPage()
        draw_top_header()
        alt_produto, alt_adicional = draw_client_header()
        c.setFont('Times', 10)

    c.setFont('Times Bold', 10)
    larg_txt = c.stringWidth('ADICIONAIS')
    pos_x = (larg_pag - larg_txt) / 2
    c.drawString(pos_x, alt_pag - 563, 'ADICIONAIS')
    c.line(15, alt_pag - 566, larg_pag - 20, alt_pag - 566)
    alt_adicional = alt_pag - 577
    c.setFont('Times', 10)

    c.line(85, alt_pag - 566.5, 85, alt_pag - 658)
    c.line(240, alt_pag - 566.5, 240, alt_pag - 658)
    c.line(330, alt_pag - 566.5, 330, alt_pag - 658)
    c.line(393, alt_pag - 566.5, 393, alt_pag - 658)
    c.line(470, alt_pag - 566.5, 470, alt_pag - 658)

    ad_count = 0
    for a in adicionais:
        adc = a.produto
        tabela1 = adc.produtotabela_set.first() if hasattr(adc, 'produtotabela_set') else None
        if ad_count >= max_por_pagina_adic:
            c.showPage()
            draw_top_header()
            alt_produto, alt_adicional = draw_client_header()
            c.setFont('Times Bold', 10)
            larg_txt = c.stringWidth('ADICIONAIS')
            pos_x = (larg_pag - larg_txt) / 2
            c.drawString(pos_x, alt_pag - 563, 'ADICIONAIS')
            alt_adicional = alt_pag - 577
            c.setFont('Times', 10)
            ad_count = 0
        valor_str1 = str(tabela1.vl_prod) if tabela1 else "0"
        valor_decimal1 = Decimal(valor_str1)
        c.drawString(20, alt_adicional, f"{adc.id}")
        c.drawString(90, alt_adicional, f"{adc.desc_prod}")
        c.drawString(245, alt_adicional, f"{adc.unidProd.nome_unidade}")
        c.drawString(335, alt_adicional, f"R$ {valor_decimal1:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c.drawString(398, alt_adicional, f"{a.quantidade}".replace(".", ","))
        c.drawString(475, alt_adicional, f"R$ {a.subtotalVenda2:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c.line(15, alt_adicional - 2, larg_pag - 20, alt_adicional - 2)
        alt_adicional -= linha_altura
        ad_count += 1

    c.setFont('Times Bold', 10)
    larg_txt = c.stringWidth('CONDIÇÕES DE PAGAMENTO')
    pos_x = (larg_pag - larg_txt) / 2
    c.drawString(pos_x, alt_pag - 668, 'CONDIÇÕES DE PAGAMENTO')
    c.line(15, alt_pag - 658, larg_pag - 20, alt_pag - 658)
    c.line(160, alt_pag - 670.5, 160, alt_pag - 736.5)
    c.line(400, alt_pag - 670.5, 400, alt_pag - 736.5)
    c.line(480, alt_pag - 670.5, 480, alt_pag - 736.5)
    c.drawString(23, alt_pag - 682, 'FORMAS DE PAGAMENTO                                     OBSERVAÇÕES                                  SUBTOTAL')
    c.drawString(405, alt_pag - 694, 'DESCONTO')
    c.drawString(405, alt_pag - 707, 'ACRÉSCIMO')
    c.drawString(405, alt_pag - 720, 'TOTAL')
    c.line(400, alt_pag - 696, larg_pag - 20, alt_pag - 696)
    c.line(400, alt_pag - 709, larg_pag - 20, alt_pag - 709)
    c.line(400, alt_pag - 722, larg_pag - 20, alt_pag - 722)
    c.line(15, alt_pag - 671, larg_pag - 20, alt_pag - 671)
    c.setFont('Times', 10)
    c.drawString(485, alt_pag - 682, "R$ " + f"{o.subtotal:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    str_desc = str(o.desconto)
    c.drawString(485, alt_pag - 693.5, "R$ " + str_desc.replace('.', ','))
    str_acres = str(o.acrescimo)
    c.drawString(485, alt_pag - 706.5, "R$ " + str_acres.replace('.', ','))
    c.drawString(485, alt_pag - 719.5, "R$ " + f"{o.total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    alt_forma = alt_pag - 694
    c.setFont('Times', 10)
    for f in o.formas_pgto.all():
        fp = f.formas_pgto
        c.drawString(20, alt_forma, f"{fp.descricao}")
        c.drawString(95, alt_forma, f"R$ {f.valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c.line(15, alt_forma - 2, larg_pag - 435, alt_forma - 2)
        alt_forma -= 13

    c.line(15, alt_pag - 684, larg_pag - 20, alt_pag - 684)
    c.setFont('Times Bold', 10)
    larg_txt = c.stringWidth('ASSINATURAS')
    pos_x = (larg_pag - larg_txt) / 2
    c.drawString(pos_x, alt_pag - 759, 'ASSINATURAS')
    larg_txt = c.stringWidth(f'{o.vinc_fil.razao_social}')
    pos_x = (larg_pag - larg_txt) / 6.50
    c.drawString(pos_x, alt_pag - 810, f'{o.vinc_fil.razao_social}')
    larg_txt = c.stringWidth('CLIENTE')
    pos_x = (larg_pag - larg_txt) / 1.25
    c.drawString(pos_x, alt_pag - 810, 'CLIENTE')
    c.line(15, alt_pag - 553, larg_pag - 20, alt_pag - 553)
    c.line(15, alt_pag - 736, larg_pag - 20, alt_pag - 736)
    c.line(15, alt_pag - 749, larg_pag - 20, alt_pag - 749)
    c.line(15, alt_pag - 762, larg_pag - 20, alt_pag - 762)
    c.line(30, alt_pag - 800, larg_pag - 360, alt_pag - 800)
    c.line(360, alt_pag - 800, larg_pag - 30, alt_pag - 800)
    c.line(15, alt_pag - 814, larg_pag - 20, alt_pag - 814)

    style = ParagraphStyle(name='Justify', alignment=TA_JUSTIFY, fontName="Times", fontSize=6)
    obs = o.obs_form_pgto or ''
    larg_max = larg_pag - 375
    parag_obs = Paragraph(obs, style)
    w, h = parag_obs.wrap(larg_max, alt_pag)
    altura_linha = 7
    num_linhas = max(1, round(h / altura_linha))
    posicoes_y = {1: alt_pag - 710,2: alt_pag - 717,3: alt_pag - 724,4: alt_pag - 721,5: alt_pag - 728,}
    pos_y = posicoes_y.get(num_linhas, alt_pag - 745)
    parag_obs.drawOn(c, 165, pos_y)

    style_rodape = ParagraphStyle(name='Justify', alignment=TA_JUSTIFY, fontName="Times Bold", fontSize=10)
    rodape = o.vinc_fil.info_orcamento
    larg_max = larg_pag - 30
    parag_rodape = Paragraph(rodape, style_rodape)
    w, h = parag_rodape.wrap(larg_max, alt_pag)
    parag_rodape.drawOn(c, 15, alt_pag - 850)

    c.save()
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="ORÇAMENTO PORTA ENROLAR - {o.id}.pdf"'
    return response