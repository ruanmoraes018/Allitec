from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Mensalidade, CobrancaPix
from .forms import MensalidadeForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from django.db import DatabaseError, IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from empresas.models import Empresa
from datetime import datetime, date, timedelta
from .pix_mp import gerar_pix_lote
import mercadopago
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import re
from django.db.models import Q

sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('mensalidades.view_mensalidade')
@login_required
def lista_mensalidades(request):
    emp = request.GET.get('emp')
    sit = request.GET.get('sit', 'Aberta')
    dt_ini = request.GET.get('dt_ini')
    dt_fim = request.GET.get('dt_fim')
    por_dt = request.GET.get('p_dt')
    reg = request.GET.get('reg', '10')
    list_p = request.GET.get('list_p', 'dt_v')
    ordem = request.GET.get('ordem', 'empresa__fantasia')
    mensalidades = Mensalidade.objects.all()
    if not dt_ini and not dt_fim and not por_dt:
        hoje = date.today()
        primeiro_dia = hoje.replace(day=1)
        if hoje.month == 12:
            ultimo_dia = hoje.replace(year=hoje.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            ultimo_dia = hoje.replace(month=hoje.month + 1, day=1) - timedelta(days=1)
        mensalidades = mensalidades.filter(
            situacao='Aberta',
            dt_venc__range=(primeiro_dia, ultimo_dia)
        )
        dt_ini = primeiro_dia.strftime('%d/%m/%Y')
        dt_fim = ultimo_dia.strftime('%d/%m/%Y')
        por_dt = 'Sim'
        sit = 'Aberta'
    if sit in ['Aberta', 'Baixada']:
        mensalidades = mensalidades.filter(situacao=sit)
    if por_dt == 'Sim' and dt_ini and dt_fim:
        try:
            dt_ini_dt = datetime.strptime(dt_ini, '%d/%m/%Y').date()
            dt_fim_dt = datetime.strptime(dt_fim, '%d/%m/%Y').date()
            if list_p == 'dt_v':
                mensalidades = mensalidades.filter(dt_venc__range=(dt_ini_dt, dt_fim_dt))
            elif list_p == 'dt_e':
                mensalidades = mensalidades.filter(created_at__date__range=(dt_ini_dt, dt_fim_dt))
            elif list_p == 'dt_p':
                mensalidades = mensalidades.filter(dt_pag__range=(dt_ini_dt, dt_fim_dt))
        except ValueError:
            mensalidades = Mensalidade.objects.none()
    empresa_selecionada = None
    if emp:
        empresa_selecionada = Empresa.objects.filter(id=emp).first()
        if empresa_selecionada:
            mensalidades = mensalidades.filter(empresa=empresa_selecionada)
            if sit and empresa_selecionada.situacao != sit:
                empresa_selecionada = None
    if reg == 'todos':
        num_pagina = mensalidades.count() or 1
    else:
        try:
            num_pagina = int(reg) if int(reg) > 0 else 10
        except ValueError:
            num_pagina = 10
    mensalidades = mensalidades.order_by(ordem)
    paginator = Paginator(mensalidades, num_pagina)
    page = request.GET.get('page')
    mensalidades = paginator.get_page(page)
    empresas = Empresa.objects.all()
    return render(request, 'mensalidades/lista.html', {
        'mensalidades': mensalidades,
        'empresas': empresas,
        'emp': emp,
        'sit': sit,
        'dt_ini': dt_ini,
        'dt_fim': dt_fim,
        'p_dt': por_dt,
        'list_p': list_p,
        'ordem': ordem,
        'reg': reg,
    })

@login_required
def lista_mensalidades_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    try:
        filtros = Q(situacao__iexact='Aberta')
        if termo_busca.isdigit():
            condicao_busca = Q(empresa__fantasia__icontains=termo_busca) | Q(id=termo_busca)
        else:
            condicao_busca = Q(empresa__fantasia__icontains=termo_busca)
        mensalidades = Mensalidade.objects.filter(filtros & condicao_busca)[:20]
        results = [{'id': mensalidade.id, 'text': f"{mensalidade.empresa.fantasia.upper()}"} for mensalidade in mensalidades]
        return JsonResponse({'results': results})
    except Exception as e:
        print(f"Erro na busca AJAX: {e}")
        return JsonResponse({'results': [], 'error': str(e)})

@login_required
def add_mensalidade(request):
    if not request.user.has_perm('mensalidades.add_mensalidade'):
        messages.info(request, 'Você não tem permissão para adicionar mensalidades.')
        return redirect('/mensalidades/lista/')
    error_messages = []
    if request.method == 'POST':
        form = MensalidadeForm(request.POST)
        if form.is_valid():
            try:
                mens = form.save(commit=False)
                mens.save()
                cid = str(mens.id)
                messages.success(request, 'Mensalidade gerada com sucesso!')
                return redirect('/mensalidades/lista/?tp=cod&s=' + cid)
            except ObjectDoesNotExist:
                error_messages.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
            except IntegrityError:
                error_messages.append("<i class='fa-solid fa-xmark'></i> Erro de integridade no banco.")
            except DatabaseError:
                error_messages.append("<i class='fa-solid fa-xmark'></i> Erro de banco de dados.")
            except Exception as e:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
        else:
            for field in form:
                for error in field.errors:
                    error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
    else:
        form = MensalidadeForm()
    return render(request, 'mensalidades/add.html', {'form': form, 'error_messages': error_messages})

@login_required
def att_mensalidade(request, id):
    mensalidade = get_object_or_404(Mensalidade, pk=id)
    form = MensalidadeForm(instance=mensalidade)
    if not request.user.has_perm('mensalidades.change_mensalidade'):
        messages.info(request, 'Você não tem permissão para editar mensalidades.')
        return redirect('/mensalidades/lista/')
    if request.method == 'POST':
        form = MensalidadeForm(request.POST, instance=mensalidade)
        if form.is_valid():
            mensalidade.save()
            next_url = request.POST.get('next') or request.GET.get('next')
            cid = str(mensalidade.id)
            messages.success(request, 'Mensalidade atualizada com sucesso!')
            if next_url:
                return redirect(next_url)
            else:
                return redirect('/mensalidades/lista/?tp=cod&s=' + cid)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'mensalidades/att.html', {'form': form, 'mensalidade': mensalidade, 'error_messages': error_messages})
    else:
        return render(request, 'mensalidades/att.html', {'form': form, 'mensalidade': mensalidade})

@login_required
def del_mensalidade(request, id):
    if not request.user.has_perm('mensalidades.delete_mensalidade'):
        messages.info(request, 'Você não tem permissão para deletar mensalidades.')
        return redirect('/mensalidades/lista/')
    mensalidade = get_object_or_404(Mensalidade, pk=id)
    mensalidade.delete()
    messages.success(request, 'Mensalidade deletada com sucesso!')
    return redirect('/mensalidades/lista/')

@login_required
def baixar_mensalidade(request, id):
    m = get_object_or_404(Mensalidade, pk=id)
    if m.situacao == 'Baixada':
        messages.warning(request, 'Mensalidade já está Baixada')
        return redirect('/mensalidades/lista/')
    elif m.situacao == 'Aberta':
        m.situacao = "Baixada"
        m.dt_pag = datetime.now()
        m.save()
        messages.success(request, 'Baixa da Mensalidade realizada com sucesso!')
        return redirect('/mensalidades/lista/')

@login_required
def estornar_mensalidade(request, id):
    m = get_object_or_404(Mensalidade, pk=id)
    if m.situacao == 'Aberta':
        messages.warning(request, 'Mensalidades Abertas não podem ser estornadas!')
        return redirect('/mensalidades/lista/')
    elif m.situacao == 'Baixada':
        m.situacao = "Aberta"
        m.save()
        messages.success(request, 'Estorno da Mensalidade realizada com sucesso!')
        return redirect('/mensalidades/lista/')

# ÁREA DO PORTAL

def login_portal(request):
    erro = None
    if request.method == "POST":
        cnpj = request.POST.get("cnpj")
        senha = request.POST.get("senha")
        cnpj = re.sub(r'\D', '', cnpj)
        try:
            empresa = Empresa.objects.get(cnpj=cnpj)
            if empresa.senha_portal == senha:
                request.session['empresa_portal_id'] = empresa.id
                return redirect('/mensalidades/portal/')
            else:
                erro = "Senha inválida"
        except Empresa.DoesNotExist:
            erro = "CNPJ não encontrado"
    return render(request, "mensalidades/login_portal.html", {"erro": erro})

def portal_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get("empresa_portal_id"):
            return redirect('/mensalidades/login/')
        return view_func(request, *args, **kwargs)
    return wrapper

def logout_portal(request):
    if "empresa_portal_id" in request.session:
        del request.session["empresa_portal_id"]
    return redirect('/mensalidades/login/')

@portal_required
def portal_pagamentos(request):
    empresa_id = request.session["empresa_portal_id"]
    empresa = Empresa.objects.get(id=empresa_id)
    hoje = date.today()
    primeiro_dia = hoje.replace(day=1)
    if hoje.month == 12:
        ultimo_dia = hoje.replace(year=hoje.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        ultimo_dia = hoje.replace(month=hoje.month + 1, day=1) - timedelta(days=1)
    mensalidades = Mensalidade.objects.filter(
        empresa=empresa,
        situacao="Aberta",
        dt_venc__range=(primeiro_dia, ultimo_dia)
    ).order_by('dt_venc')
    return render(request, "mensalidades/portal_pagamentos.html", {
        "empresa": empresa,
        "mensalidades": mensalidades,
    })

def visualizar_pix(request, id):
    cobranca = CobrancaPix.objects.get(mp_payment_id=id)

    return render(request, "mensalidades/pix.html", {
        "qr_code": cobranca.qr_code_base64,
        "copia_cola": cobranca.qr_code,
        "valor": cobranca.valor,
        "cobranca_id": str(cobranca.mp_payment_id),  # <- FORÇA string
    })

def status_pix(request, id):
    try:
        cobranca = CobrancaPix.objects.get(mp_payment_id=id)
        return JsonResponse({"pago": cobranca.pago})
    except CobrancaPix.DoesNotExist:
        return JsonResponse({"pago": False})

@portal_required
def gerar_pix_lote_view(request):
    if request.method != "POST":
        return JsonResponse({"erro": "Método inválido"}, status=405)
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"erro": "JSON inválido"}, status=400)
    ids = data.get("mensalidades", [])
    if not ids:
        return JsonResponse({"erro": "Nenhuma mensalidade enviada"}, status=400)
    empresa = Empresa.objects.get(id=request.session["empresa_portal_id"])
    mensalidades = Mensalidade.objects.filter(
        id__in=ids,
        empresa=empresa,
        situacao="Aberta"
    )
    if not mensalidades.exists():
        return JsonResponse({"erro": "Mensalidades inválidas"}, status=400)
    cobranca = gerar_pix_lote(mensalidades)   # <-- AQUI
    return JsonResponse({
        "redirect": f"/mensalidades/pix/{cobranca.mp_payment_id}/"
    })

@csrf_exempt
def webhook_mp(request):
    if request.GET.get("type") != "payment":
        return JsonResponse({"ok": True})
    payment_id = request.GET.get("data.id")
    payment_info = sdk.payment().get(payment_id)["response"]
    if payment_info["status"] != "approved":
        return JsonResponse({"ok": True})
    try:
        cobranca = CobrancaPix.objects.get(mp_payment_id=payment_id)
    except CobrancaPix.DoesNotExist:
        return JsonResponse({"erro": "cobranca nao encontrada"})
    cobranca.pago = True
    cobranca.save()
    for mensalidade in cobranca.mensalidades.all():
        mensalidade.situacao = "Baixada"
        mensalidade.dt_pag = datetime.now()
        mensalidade.vl_pago = mensalidade.valor_total
        mensalidade.save()
    return JsonResponse({"ok": True})

