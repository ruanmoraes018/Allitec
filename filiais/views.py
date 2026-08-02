from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from .models import Filial, LogUsuario
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import re
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from cryptography.x509.oid import NameOID
import unicodedata
from django.core.paginator import Paginator
from .forms import FilialForm, FilialReadOnlyForm, EmpresaLoginForm, FilialFinanceiroForm, FilialFiscalForm, FilialOrcamentoForm, FilialContatoForm, FilialEstoqueForm, FilialImpressaoForm, FilialObservacaoForm
from util.permissoes import verifica_permissao
from django.http import JsonResponse
from orcamentos.models import Orcamento, PortaProduto, OrcamentoFormaPgto, PortaOrcamento
from contas.forms import SuperuserLoginForm
from notifications.models import Notification
from estados.models import Estado
from cidades.models import Cidade
from bairros.models import Bairro
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from core.pagamentos.webhooks import processar_webhook
from pedidos.models import Pagamento
from django.utils import timezone
import logging
from calendar import monthrange
from datetime import datetime, time
from django.db.models import Count
from django.db.models.functions import TruncDate
from collections import defaultdict, Counter
from django.db.models import Sum
from decimal import Decimal
import json
from util.logs import gerar_alteracoes, registrar_log
from produtos.models import Alerta
from django.db import transaction
from .certificado import CertificadoService

logger = logging.getLogger(__name__)

@login_required
def validar_certificado(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "erro": "Método inválido."}, status=405)
    arquivo = request.FILES.get("certificado")
    senha = request.POST.get("senha", "")
    cnpj_filial = re.sub(r"\D", "", request.POST.get("cnpj_filial", ""))
    if not arquivo:
        return JsonResponse({"ok": False, "erro": "Selecione um certificado."})
    if not senha:
        return JsonResponse({"ok": False, "erro": "Informe a senha do certificado."})
    try:
        cert = CertificadoService(arquivo, senha, cnpj_filial)
        dados = cert.resumo()
        validade = cert.validade()
        return JsonResponse({
            "ok": True, "titular": dados["nome"], "cnpj": dados["cnpj"], "cnpj_formatado": dados["cnpj_formatado"], "cnpj_ok": dados["cnpj_confere_filial"],
            "inicio_validade": validade["inicio"].strftime("%d/%m/%Y"), "fim_validade": validade["fim"].strftime("%d/%m/%Y"), "dias_restantes": validade["dias_restantes"],
            "vencido": validade["expirado"], "vence_breve": (0 <= validade["dias_restantes"] <= 30), "possui_chave_privada": dados["possui_chave_privada"],
        })
    except Exception as e:
        return JsonResponse({"ok": False, "erro": str(e)})

def validar_certificado_filial(filial, arquivo=None, senha=None):

    certificado = arquivo or filial.fiscal.certificado

    if not certificado:
        return True

    senha_cert = senha or filial.fiscal.senha_certificado

    if not senha_cert:
        raise Exception("Senha do certificado não informada.")

    cert = CertificadoService(
        certificado,
        senha_cert.strip(),
        filial.cnpj
    )

    validade = cert.validade()

    if not validade["valido"]:
        raise Exception("O certificado digital está expirado ou ainda não é válido.")

    if not cert.cnpj_confere():
        raise Exception("O CNPJ do certificado não pertence à filial.")

    return True 

@login_required
def validar_certificado_salvo(request, codigo):
    empresa = request.user.empresa
    filial = get_object_or_404(Filial, codigo=codigo, vinc_emp=empresa)
    print("FILIAL:", filial)
    print("SENHA:", filial.fiscal.senha_certificado)
    try:
        validar_certificado_filial(filial)

        cert = CertificadoService(
            filial.fiscal.certificado,
            filial.fiscal.senha_certificado,
            filial.cnpj
        )

        dados = cert.resumo()
        validade = cert.validade()
        return JsonResponse({
            "ok": True,
            "titular": dados["nome"],
            "cnpj_formatado": dados["cnpj_formatado"],
            "inicio_validade": validade["inicio"].strftime("%d/%m/%Y"),
            "fim_validade": dados["fim_validade"].strftime("%d/%m/%Y"),
            "dias_restantes": dados["dias_restantes"],
            "vencido": dados["expirado"],
            "vence_breve": dados["dias_restantes"] <= 30,
        })

    except Exception as e:
        return JsonResponse({
            "ok": False,
            "erro": str(e)
        })

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

def login_superusuario(request):
    if request.method == "POST":
        form = SuperuserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_superuser:
                login(request, user)
                return redirect("/empresas/lista/")
            else: messages.error(request, "Apenas superusuários podem acessar por aqui.")
        else: messages.error(request, "Usuário ou senha incorretos.")
    else: form = SuperuserLoginForm()
    return render(request, 'registration/login_superuser.html', {'form': form})

def login_filial(request):
    if request.method == "POST":
        form = EmpresaLoginForm(request.POST)
        form.request = request
        if form.is_valid():
            usuario = form.cleaned_data["user"]
            login(request, usuario)
            registrar_log(
                request=request, tipo="LOGIN", modulo="Autenticação", objeto=usuario.username,
                objeto_id=usuario.id, descricao="Realizou login no sistema.",
                alteracoes={"IP": request.META.get("REMOTE_ADDR"), "Navegador": request.META.get("HTTP_USER_AGENT"),}
            )
            return redirect("inicio")
        for error in form.non_field_errors():
            messages.error(request, error)
    else:
        form = EmpresaLoginForm()
    return render(request, "registration/login.html", {"form": form})

@login_required
def logout_view(request):
    usuario = request.user  # guarda antes de deslogar
    registrar_log(
        request=request, tipo="LOGOUT", modulo="Autenticação", objeto=usuario.username, 
        objeto_id=usuario.id, descricao="Encerrou a sessão no sistema.",
        alteracoes={"IP": request.META.get("REMOTE_ADDR"), "Navegador": request.META.get("HTTP_USER_AGENT"),}
    )
    logout(request)
    return redirect("/accounts/login")

def verificar_ou_criar_localizacao(request):
    estado_nome = request.GET.get('estado')
    cidade_nome = request.GET.get('cidade')
    bairro_nome = request.GET.get('bairro')
    if not estado_nome or not cidade_nome: return JsonResponse({'erro': 'Estado e cidade são obrigatórios.'}, status=400)
    # Normalização
    estado_nome = estado_nome.strip().upper()
    cidade_nome = cidade_nome.strip().upper()
    bairro_nome = bairro_nome.strip().upper() if bairro_nome else None
    # Estado
    estado = Estado.objects.filter(nome_estado__iexact=estado_nome, vinc_emp=request.user.empresa).first()
    if not estado: estado = Estado.objects.create(nome_estado=estado_nome, vinc_emp=request.user.empresa)
    # Cidade
    cidade = Cidade.objects.filter(nome_cidade__iexact=cidade_nome, vinc_emp=request.user.empresa).first()
    if not cidade: cidade = Cidade.objects.create(nome_cidade=cidade_nome, vinc_emp=request.user.empresa)
    # Bairro
    bairro = None
    if bairro_nome:
        bairro = Bairro.objects.filter(nome_bairro__iexact=bairro_nome, vinc_emp=request.user.empresa).first()
        if not bairro: bairro = Bairro.objects.create(nome_bairro=bairro_nome, vinc_emp=request.user.empresa)
    response = {'estado_id':estado.codigo,'estado_nome':estado.nome_estado,'cidade_id':cidade.codigo,'cidade_nome':cidade.nome_cidade,'bairro_id':bairro.codigo if bairro else "",'bairro_nome':bairro.nome_bairro if bairro else "",}
    return JsonResponse(response)

@login_required
def verificar_parcelas(request):
    filial = request.user.filial_user
    parcelas = request.GET.get('parcelas')
    dias = request.GET.get('dias')
    if parcelas is not None:
        parcelas = int(parcelas)
        if parcelas > filial.max_parcelas: return JsonResponse({'permitido': False, 'maximo': filial.max_parcelas})
    if dias is not None:
        dias = int(dias)
        if dias > filial.max_dias_intervalo: return JsonResponse({'permitido': False, 'maximo': filial.max_dias_intervalo})
    return JsonResponse({'permitido': True})

@login_required
def notificacoes_ajax(request):
    notificacoes = Notification.objects.filter(recipient=request.user, unread=True)
    alertas = Alerta.objects.filter(empresa=request.user.empresa, status='Aberto').order_by('-criado_em')
    data = []
    # Processa Notificações Pessoais (Ex: Solicitações)
    for n in notificacoes:
        # Garante que 'dados' seja um dicionário mesmo se n.data for None ou String
        dados = n.data if isinstance(n.data, dict) else {}
        data.append({'tipo': 'NOTIFICACAO', 'id': n.id, 'verb': n.verb,
            'description': n.description, 'solicitacao_id': dados.get('solicitacao_id'),
        })
    # Processa Alertas Globais da Empresa (Ex: Estoque, Contas)
    for a in alertas:
        data.append({'tipo': 'ALERTA', 'id': a.id, 'alerta_tipo': a.tipo, 'titulo': a.titulo,
            'description': a.descricao, 'referencia': a.referencia, 'url': a.url,
        })
    return JsonResponse({'notificacoes': data})

@verifica_permissao('filiais.view_filial')
@login_required
def lista_filiais(request):
    s = request.GET.get('s')               # texto de busca
    tp = request.GET.get('tp')             # tipo de busca (desc ou cod)
    f_s = request.GET.get('sit')           # situação: Ativa / Inativa
    t_pes = request.GET.get('t_pes')       # tipo pessoa: Física / Jurídica
    dt_ini = request.GET.get('dt_ini')     # data inicial
    dt_fim = request.GET.get('dt_fim')     # data final
    p_dt = request.GET.get('p_dt')         # filtrar por data? Sim / Não
    reg = request.GET.get('reg', '10')     # registros por página
    empresa = request.user.empresa
    filiais = Filial.objects.filter(vinc_emp=empresa)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        filiais = filiais.filter(fantasia_normalizado__icontains=norm_s).order_by('fantasia')
    elif tp == 'cod' and s:
        try: filiais = filiais.filter(codigo__iexact=s).order_by('fantasia')
        except ValueError: filiais = Filial.objects.none()
    if p_dt == 'Sim' and dt_ini and dt_fim:
        try:
            dt_ini_dt = datetime.strptime(dt_ini, '%d/%m/%Y').date()
            dt_fim_dt = datetime.strptime(dt_fim, '%d/%m/%Y').date()
            filiais = filiais.filter(dt_criacao__range=(dt_ini_dt, dt_fim_dt))
        except ValueError: filiais = Filial.objects.none()
    if f_s in ['Ativa', 'Inativa']: filiais = filiais.filter(situacao=f_s)
    if t_pes in ['Física', 'Jurídica']: filiais = filiais.filter(pessoa=t_pes)
    # Paginação
    if reg == 'todos': num_pagina = filiais.count() or 1
    else:
        try: num_pagina = int(reg)
        except ValueError: num_pagina = 10
    paginator = Paginator(filiais, num_pagina)
    page = request.GET.get('page')
    filiais = paginator.get_page(page)
    return render(request, 'filiais/lista.html', {'filiais': filiais, 's': s, 'tp': tp, 't_pes': t_pes, 'dt_ini': dt_ini, 'dt_fim': dt_fim, 'p_dt': p_dt, 'reg': reg})

from django.db import models
@login_required
def filiais_vinculadas_ajax(request):
    termo_busca = request.GET.get('term', '')
    empresa = request.user.empresa
    filial_principal = empresa
    if filial_principal is None: return JsonResponse({'results': []})
    filiais = Filial.objects.filter(models.Q(vinculada_a=filial_principal) | models.Q(codigo=filial_principal.codigo), situacao='Ativa', fantasia__icontains=termo_busca).values('codigo', 'fantasia')
    results = [{'id': f['codigo'], 'text': f['fantasia'].upper()} for f in filiais]
    return JsonResponse({'results': results})

@login_required
def lista_filiais_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit(): condicao_busca = Q(fantasia__icontains=termo_busca) | Q(codigo=termo_busca)
        else: condicao_busca = Q(fantasia__icontains=termo_busca)
        filiais = Filial.objects.filter(condicao_busca, vinc_emp=empresa)
        # Se o usuário utiliza filiais permitidas, limita a consulta
        if request.user.opfilial == "0":
            filiais = filiais.filter(id__in=request.user.filiais_permitidas.all())
        filiais = filiais[:20]
        results = [{'id': filial.codigo, 'text': filial.fantasia.upper()} for filial in filiais]
        return JsonResponse({'results': results})
    except Exception as e:
        return JsonResponse({'results': [], 'error': str(e)})

@login_required
def dados_filiais_js(request):
    empresa = request.user.empresa
    if not empresa: return JsonResponse({}, status=403)
    filiais = (
    Filial.objects.filter(vinc_emp=empresa, situacao='Ativa').select_related(
        'orcamento_porta', 'financeiro', 'fiscal', 'contato',
        'estoque', 'impressao', 'observacoes', 'tb_preco',
        'cli', 'tec', 'vendedor',
    ))
    data = {
        str(f.codigo): {
            'cli': f.cli.codigo if f.cli else None, 'cli_nome': f.cli.fantasia if f.cli else None, 'tec': f.tec.codigo if f.tec else None,
            'vend': f.vendedor.codigo if f.vendedor else None, 'vend_nome': f.vendedor.fantasia if f.vendedor else None,
            'tb_preco': f.tb_preco.codigo if f.tb_preco else None, 'tb_preco_nome': f.tb_preco.descricao if f.tb_preco else None, 'agrupa_itens': f.agrupa_itens,
            'mt_qt_lam':f.orcamento_porta.mt_qt_lam if f.orcamento_porta else None,'multi_m2':float(f.orcamento_porta.multi_m2) if f.orcamento_porta and f.orcamento_porta.multi_m2 is not None else 0,
            'multi_lg_corte1': float(f.orcamento_porta.multi_lg_corte1) if f.orcamento_porta and f.orcamento_porta.multi_lg_corte1 is not None else 0,
            'multi_lg_corte2': float(f.orcamento_porta.multi_lg_corte2) if f.orcamento_porta and f.orcamento_porta.multi_lg_corte2 is not None else 0,
            'multi_lg_corte3': float(f.orcamento_porta.multi_lg_corte3) if f.orcamento_porta and f.orcamento_porta.multi_lg_corte3 is not None else 0,
        }
        for f in filiais
    }
    return JsonResponse(data)

@login_required
def add_filial(request):
    if not request.user.has_perm('filiais.add_filial'):
        messages.info(request, 'Você não tem permissão para adicionar filiais.')
        return redirect('/filiais/lista/')
    empresa = request.user.empresa
    if not empresa:
        messages.error(request, 'Erro crítico: Seu usuário não está vinculado a nenhuma empresa cadastrada.')
        return redirect('/filiais/lista/')
    try:
        filial_principal = Filial.objects.get(vinc_emp=empresa, principal=True)
    except Filial.DoesNotExist:
        messages.error(request, 'Filial principal não encontrada para este usuário.')
        return redirect('/filiais/lista/')
    qtd_permitida = empresa.qtd_filial
    total_filiais_vinculadas = (1 + filial_principal.filiais_secundarias.filter(vinc_emp=empresa, situacao='Ativa').count())
    if total_filiais_vinculadas >= qtd_permitida:
        messages.warning(request, f'Limite de {qtd_permitida} filial(is) ativa(s) atingido para sua empresa.')
        return redirect('/filiais/lista/')
    if request.method == "POST":
        form = FilialForm(data=request.POST, files=request.FILES, empresa=empresa)
        f_financeiro = FilialFinanceiroForm(data=request.POST, empresa=empresa)
        f_fiscal = FilialFiscalForm(data=request.POST, files=request.FILES, empresa=empresa)
        f_orcamento = FilialOrcamentoForm(data=request.POST, empresa=empresa)
        f_contato = FilialContatoForm(data=request.POST, empresa=empresa)
        f_estoque = FilialEstoqueForm(data=request.POST, empresa=empresa)
        f_impressao = FilialImpressaoForm( data=request.POST, empresa=empresa)
        f_observacao = FilialObservacaoForm(data=request.POST, empresa=empresa)
        if (
            form.is_valid()
            and f_financeiro.is_valid()
            and f_fiscal.is_valid()
            and f_orcamento.is_valid()
            and f_contato.is_valid()
            and f_estoque.is_valid()
            and f_impressao.is_valid()
            and f_observacao.is_valid()
        ):
            try:
                with transaction.atomic():
                    nova_filial = form.save(commit=False)
                    nova_filial.vinc_emp = empresa
                    nova_filial.vinculada_a = filial_principal
                    nova_filial.principal = False
                    nova_filial.situacao = "Ativa"
                    nova_filial.save()
                    financeiro = f_financeiro.save(commit=False)
                    fiscal = f_fiscal.save(commit=False)
                    orcamento = f_orcamento.save(commit=False)
                    contato = f_contato.save(commit=False)
                    estoque = f_estoque.save(commit=False)
                    impressao = f_impressao.save(commit=False)
                    observacao = f_observacao.save(commit=False)
                    financeiro.filial = nova_filial
                    fiscal.filial = nova_filial
                    orcamento.filial = nova_filial
                    contato.filial = nova_filial
                    estoque.filial = nova_filial
                    impressao.filial = nova_filial
                    observacao.filial = nova_filial
                    financeiro.save()
                    fiscal.save()
                    orcamento.save()
                    contato.save()
                    estoque.save()
                    impressao.save()
                    observacao.save()
                    registrar_log(request, "CRIAR", "Filial", nova_filial.fantasia,
                        f"Adicionou a filial: {nova_filial.codigo} - {nova_filial.fantasia}",
                        nova_filial.id, gerar_alteracoes(obj_novo=nova_filial)
                    )
                messages.success(request, "Filial cadastrada com sucesso.")
                return redirect("/filiais/lista/")
            except Exception as e:
                messages.error(request, f"Erro ao cadastrar filial: {e}")
    else:
        form = FilialForm(empresa=empresa)
        f_financeiro = FilialFinanceiroForm(empresa=empresa)
        f_fiscal = FilialFiscalForm(empresa=empresa)
        f_orcamento = FilialOrcamentoForm(empresa=empresa)
        f_contato = FilialContatoForm(empresa=empresa)
        f_estoque = FilialEstoqueForm(empresa=empresa)
        f_impressao = FilialImpressaoForm(empresa=empresa)
        f_observacao = FilialObservacaoForm(empresa=empresa)
    return render(request, "filiais/add_filial.html",{
        "form": form, "f_financeiro": f_financeiro, "f_fiscal": f_fiscal,
        "f_orcamento": f_orcamento, "f_contato": f_contato, "f_estoque": f_estoque,
        "f_impressao": f_impressao, "f_observacao": f_observacao,
    })

@login_required
def att_filial(request, codigo):
    empresa = request.user.empresa
    filial = get_object_or_404(Filial, codigo=codigo, vinc_emp=empresa)
    if not request.user.has_perm("filiais.change_filial"):
        messages.info(request, "Você não tem permissão para editar filiais.")
        return redirect("/filiais/lista/")
    it_old = Filial.objects.get(codigo=filial.codigo, vinc_emp=empresa)
    # Garante que filiais antigas tenham todos os registros relacionados
    filial.garantir_configuracoes()
    financeiro = filial.financeiro
    fiscal = filial.fiscal
    orcamento = filial.orcamento_porta
    contato = filial.contato
    estoque = filial.estoque
    impressao = filial.impressao
    observacoes = filial.observacoes
    if request.method == "POST":
        form = FilialForm(request.POST, request.FILES, instance=filial, empresa=empresa)
        f_financeiro = FilialFinanceiroForm(request.POST, instance=financeiro, empresa=empresa)
        f_fiscal = FilialFiscalForm(request.POST, request.FILES, instance=fiscal, empresa=empresa)
        f_orcamento = FilialOrcamentoForm(request.POST, instance=orcamento, empresa=empresa)
        f_contato = FilialContatoForm(request.POST, instance=contato, empresa=empresa)
        f_estoque = FilialEstoqueForm(request.POST, instance=estoque, empresa=empresa)
        f_impressao = FilialImpressaoForm(request.POST, instance=impressao, empresa=empresa)
        f_observacao = FilialObservacaoForm(request.POST, instance=observacoes, empresa=empresa)
        if (
            form.is_valid()
            and f_financeiro.is_valid()
            and f_fiscal.is_valid()
            and f_orcamento.is_valid()
            and f_contato.is_valid()
            and f_estoque.is_valid()
            and f_impressao.is_valid()
            and f_observacao.is_valid()
        ):
            try:
                validar_certificado_filial(filial, request.FILES.get("certificado"), request.POST.get("senha_certificado"))
                with transaction.atomic():
                    filial = form.save()
                    f_financeiro.save()
                    f_fiscal.save()
                    f_orcamento.save()
                    f_contato.save()
                    f_estoque.save()
                    f_impressao.save()
                    f_observacao.save()
                    registrar_log(request, "ALTERAR", "Filial", filial.fantasia,
                        f"Alterou a filial: {filial.codigo} - {filial.fantasia}",
                        filial.id, gerar_alteracoes(it_old, filial)
                    )
                messages.success(request, "Filial atualizada com sucesso.")
                next_url = (request.POST.get("next") or request.GET.get("next"))
                if next_url:
                    return redirect(next_url)
                return redirect(f"/filiais/lista/?tp=cod&s={filial.codigo}")
            except Exception as e:
                messages.error(request, f"Erro ao atualizar filial: {e}")
        else:
            error_messages = []
            for formulario in (form, f_financeiro, f_fiscal, f_orcamento, f_contato, f_estoque, f_impressao, f_observacao,):
                for field in formulario:
                    for erro in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {erro}")
            return render(request, "filiais/att_filial.html",{
                "form": form, "filial": filial, "f_financeiro": f_financeiro,
                "f_fiscal": f_fiscal, "f_orcamento": f_orcamento, "f_contato": f_contato,
                "f_estoque": f_estoque, "f_impressao": f_impressao, "f_observacao": f_observacao, "error_messages": error_messages, "tem_certificado": bool(filial.fiscal.certificado),
            })

    else:
        form = FilialForm(instance=filial, empresa=empresa)
        f_financeiro = FilialFinanceiroForm(instance=financeiro, empresa=empresa)
        f_fiscal = FilialFiscalForm(instance=fiscal, empresa=empresa)
        f_orcamento = FilialOrcamentoForm(instance=orcamento, empresa=empresa)
        f_contato = FilialContatoForm(instance=contato, empresa=empresa)
        f_estoque = FilialEstoqueForm(instance=estoque, empresa=empresa)
        f_impressao = FilialImpressaoForm(instance=impressao, empresa=empresa)
        f_observacao = FilialObservacaoForm(instance=observacoes, empresa=empresa)
    return render(request, "filiais/att_filial.html",{
        "form": form, "filial": filial, "f_financeiro": f_financeiro, "f_fiscal": f_fiscal,
        "f_orcamento": f_orcamento, "f_contato": f_contato, "f_estoque": f_estoque,
        "f_impressao": f_impressao, "f_observacao": f_observacao, "tem_certificado": bool(filial.fiscal.certificado),
    })

@login_required
def del_filial(request, codigo):
    empresa = request.user.empresa
    filial = get_object_or_404(Filial, codigo=codigo, vinc_emp=empresa)
    if not request.user.has_perm('filiais.delete_filial'):
        messages.info(request, 'Você não tem permissão para deletar filiais.')
        return redirect('/filiais/lista/')
    if filial.vinculada_a != request.user.usuario.filial:
        messages.error(request, 'Você não tem permissão para deletar esta filial.')
        return redirect('/filiais/lista/')
    if request.method == 'POST':
        registrar_log(
            request, "EXCLUIR", "Filial", filial.fantasia,
            f"Excluiu a filial: {filial.codigo} - {filial.fantasia}",
            filial.id, gerar_alteracoes(obj_antigo=filial)
        )
        filial.delete()
        messages.success(request, 'Filial excluída com sucesso.')
        return redirect('/filiais/lista/')
    form = FilialReadOnlyForm(instance=filial, empresa=empresa)
    return render(request, 'filiais/del_filial.html', {'filial': filial, 'form': form})

@login_required
def logout_view_superuser(request):
    logout(request)
    return redirect('/accounts/login-superuser')

@login_required
def dashboard(request):
    if request.user.is_superuser:
        return redirect('/empresas/lista/')
    dt_ini = request.GET.get("dt_ini")
    dt_fim = request.GET.get("dt_fim")
    filial = request.GET.get("filial")
    filial_fantasia = None
    hoje = datetime.today()
    ultimos_logs = (LogUsuario.objects.filter(usuario=request.user, data__date=hoje).order_by("-data")[:4])
    logs_dia = (LogUsuario.objects.filter(usuario=request.user, data__date=hoje).order_by("-data"))
    primeiro_dia = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ultimo_dia = hoje.replace(day=monthrange(hoje.year, hoje.month)[1], hour=23, minute=59, second=59, microsecond=999999)
    if filial:
        filial = int(filial)
        filial_fantasia = Filial.objects.filter(codigo=filial, vinc_emp=request.user.empresa).first()
        filial_fantasia = filial_fantasia
    else:
        filial = request.user.filial_user.codigo
        filial_fantasia = request.user.filial_user.fantasia
    try:
        if dt_ini and dt_fim:
            data_inicial = datetime.strptime(dt_ini,"%d/%m/%Y").date()
            data_final = datetime.strptime(dt_fim,"%d/%m/%Y").date()
            dt_ini_dt = datetime.combine(data_inicial,time.min)
            dt_fim_dt = datetime.combine(data_final,time.max)
        else:
            raise ValueError
    except:
        dt_ini_dt = primeiro_dia
        dt_fim_dt = ultimo_dia
        data_inicial = None
        data_final = None
        dt_ini = ""
        dt_fim = ""
        filial = request.user.filial_user.codigo
    qs = (
        Orcamento.objects.filter(vinc_emp=request.user.empresa, vinc_fil__codigo=filial, dt_emi__range=(dt_ini_dt,dt_fim_dt))
        .select_related("solicitante","cli").prefetch_related("formas_pgto").order_by("dt_emi")
    )
    total_orcamentos = qs.count()
    abertos = qs.filter(situacao="Aberto").count()
    faturados = qs.filter(situacao="Faturado").count()
    cancelados = qs.filter(situacao="Cancelado").count()
    total_abertos = total_faturados = total_cancelados = 0
    tecnicos = defaultdict(lambda:{"nome":"","qtd":0,"total":0})
    clientes = defaultdict(lambda:{"nome":"","qtd":0,"total":0})
    filiais = Filial.objects.filter(vinc_emp=request.user.empresa).order_by("fantasia")
    faturado_dia = defaultdict(lambda: Decimal("0.00"))
    for orc in qs:
        valor = sum(f.valor for f in orc.formas_pgto.all())
        if orc.situacao == "Aberto":
            total_abertos += valor
        elif orc.situacao == "Cancelado":
            total_cancelados += valor
        elif orc.situacao == "Faturado":
            total_faturados += valor
            if orc.solicitante:
                t = tecnicos[orc.solicitante.codigo]
                t["nome"] = orc.solicitante.nome
                t["qtd"] += 1
                t["total"] += valor
            if orc.cli:
                c = clientes[orc.cli.codigo]
                c["nome"] = orc.cli.fantasia
                c["qtd"] += 1
                c["total"] += valor
            faturado_dia[orc.dt_emi.strftime("%d/%m")] += valor
    taxa_conversao = ((faturados/total_orcamentos)*100 if total_orcamentos else 0)
    ticket_medio = ((total_abertos+total_faturados+total_cancelados) / total_orcamentos if total_orcamentos else 0)
    media_valor_fat = (total_faturados/faturados if faturados else 0)
    evolucao = (qs.annotate(dia=TruncDate("dt_emi")).values("dia").annotate(total=Count("codigo")).order_by("dia"))
    dias = [e["dia"].strftime("%d/%m") for e in evolucao if e["dia"]]
    qtd_dias = [e["total"] for e in evolucao]
    ranking_tecnicos = sorted([{"id":k,**v} for k,v in tecnicos.items()], key=lambda x:x["total"], reverse=True)
    ranking_clientes = sorted([{"id":k,**v} for k,v in clientes.items()], key=lambda x:x["total"], reverse=True)
    produtos_qtd = (
        PortaProduto.objects.filter(porta__orcamento__in=qs).values("produto__desc_prod", "produto__unidProd__nome_unidade").annotate(quantidade=Sum("quantidade"), valor=Sum("valor_total")).order_by("-quantidade")[:10]
    )
    produtos_vl = (
        PortaProduto.objects.filter(porta__orcamento__in=qs).values("produto__desc_prod").annotate(quantidade=Sum("quantidade"), valor=Sum("valor_total")).order_by("-valor")[:10]
    )
    formas = (OrcamentoFormaPgto.objects.filter(orcamento__in=qs).values("formas_pgto__descricao").annotate(valor=Sum("valor")).order_by("-valor"))
    status_producao = (qs.values("status").annotate(total=Count("codigo")).order_by("-total"))
    status_pagamento = (qs.values("status_pagamento").annotate(total=Count("codigo")).order_by("-total"))
    cores = (qs.values("cor").annotate(total=Count("codigo")).order_by("-total"))
    # CARACTERÍSTICAS DOS PORTÕES
    caracteristicas = Counter()
    for o in qs:
        pintura = o.tp_pintura or "Não informado"
        portao = "Com Portão Social" if o.portao_social == "Sim" else "Sem Portão Social"
        chave = f"{pintura} - {portao}"
        caracteristicas[chave] += 1
    caracteristicas_labels = list(caracteristicas.keys())
    caracteristicas_valores = list(caracteristicas.values())
    # VALOR POR SITUAÇÃO
    situacao_valores = [float(total_abertos), float(total_faturados), float(total_cancelados),]
    situacao_labels = ["Abertos", "Faturados", "Cancelados",]
    # FORMAS DE PAGAMENTO
    formas_labels = [f["formas_pgto__descricao"] or "Não informado" for f in formas]
    formas_valores = [float(f["valor"] or 0) for f in formas]
    # PRODUTOS MAIS VENDIDOS
    produtos_qtd_labels = [p["produto__desc_prod"] or "Sem descrição" for p in produtos_qtd]
    produtos_quantidade = [float(p["quantidade"] or 0) for p in produtos_qtd]
    produtos_unidades = [p["produto__unidProd__nome_unidade"] or "" for p in produtos_qtd]
    produtos_vl_labels = [p["produto__desc_prod"] or "Sem descrição" for p in produtos_vl]
    produtos_valores = [float(p["valor"] or 0) for p in produtos_vl]
    # STATUS PRODUÇÃO
    status_prod_labels = [s["status"] or "Não informado" for s in status_producao]
    status_prod_valores = [s["total"] for s in status_producao]
    # STATUS PAGAMENTO
    status_pgto_labels = [s["status_pagamento"] or "Não informado" for s in status_pagamento]
    status_pgto_valores = [s["total"] for s in status_pagamento]
    # CORES
    cores_labels = [c["cor"] or "Não informado" for c in cores]
    cores_valores = [c["total"] for c in cores]
    portas = PortaOrcamento.objects.filter(orcamento__in=qs)
    total_m2 = sum(float(p.m2 or 0) for p in portas)
    peso_total = sum(float(p.peso or 0) for p in portas)
    dias = []
    for o in qs.filter(situacao="Faturado"):
        if o.dt_fat and o.dt_emi:
            dias.append((o.dt_fat.date()-o.dt_emi.date()).days)
    tempo_medio = sum(dias)/len(dias) if dias else 0
    tecnicos_labels = [t["nome"] for t in ranking_tecnicos]
    tecnicos_valores = [float(t["total"]) for t in ranking_tecnicos]
    clientes_labels = [c["nome"] for c in ranking_clientes]
    clientes_valores = [float(c["total"]) for c in ranking_clientes]
    faturamento_labels = list(faturado_dia.keys())
    faturamento_valores = [float(v) for v in faturado_dia.values()]
    context = {
        "ultimos_logs": ultimos_logs,
        "logs_dia": logs_dia,
        "orcamentos_no_intervalo":qs,
        "orcamentos_abertos":abertos,
        "orcamentos_faturados":faturados,
        "orcamentos_cancelados":cancelados,
        "total_abertos":total_abertos,
        "total_faturados":total_faturados,
        "total_cancelados":total_cancelados,
        "media_valor_fat":media_valor_fat,
        "ticket_medio":ticket_medio,
        "taxa_conversao":round(taxa_conversao,1),
        "dias":dias,
        "qtd_dias":qtd_dias,
        "ranking_tecnicos":ranking_tecnicos,
        "ranking_clientes":ranking_clientes,
        "tecnicos": tecnicos,
        "clientes": clientes,
        "filiais": filiais,
        "filial": filial,
        "filial_fantasia": filial_fantasia,
        "formas_pgto":formas,
        "produtos_qtd_labels": json.dumps(produtos_qtd_labels),
        "produtos_quantidade": json.dumps(produtos_quantidade),
        "produtos_unidades": json.dumps(produtos_unidades),
        "produtos_vl_labels": json.dumps(produtos_vl_labels),
        "produtos_valores": json.dumps(produtos_valores),
        "status_producao":status_producao,
        "status_pagamento":status_pagamento,
        "cores":cores,
        "caracteristicas_labels": json.dumps(caracteristicas_labels),
        "caracteristicas_valores": json.dumps(caracteristicas_valores),
        "total_m2":total_m2,
        "peso_total":peso_total,
        "tempo_medio":tempo_medio,
        "primeiro_dia_mes":primeiro_dia,
        "ultimo_dia_mes":ultimo_dia,
        "dt_ini":dt_ini,
        "dt_fim":dt_fim,
        "data_inicial":data_inicial,
        "data_final":data_final,
        "data_atual":hoje,
        "tecnicos_labels": json.dumps(tecnicos_labels),
        "tecnicos_valores": json.dumps(tecnicos_valores),
        "clientes_labels": json.dumps(clientes_labels),
        "clientes_valores": json.dumps(clientes_valores),
        # NOVOS GRÁFICOS
        "situacao_labels": json.dumps(situacao_labels),
        "situacao_valores": json.dumps(situacao_valores),
        "formas_labels": json.dumps(formas_labels),
        "formas_valores": json.dumps(formas_valores),
        "status_prod_labels": json.dumps(status_prod_labels),
        "status_prod_valores": json.dumps(status_prod_valores),
        "status_pgto_labels": json.dumps(status_pgto_labels),
        "status_pgto_valores": json.dumps(status_pgto_valores),
        "cores_labels": json.dumps(cores_labels),
        "cores_valores": json.dumps(cores_valores),
        "faturamento_labels": json.dumps(faturamento_labels),
        "faturamento_valores": json.dumps(faturamento_valores),
    }
    return render(request,"dashbord.html",context)

@csrf_exempt
def webhook_pagamentos(request):
    logger.error("=" * 80)
    logger.error("WEBHOOK RECEBIDO")
    logger.error("Método: %s", request.method)
    logger.error("Headers: %s", dict(request.headers))
    logger.error("Body: %s", request.body.decode("utf-8", errors="ignore"))
    logger.error("=" * 80)
    result = processar_webhook(request)
    print("RESULT:", result)
    if not result:
        print("RESULT É NONE")
        return JsonResponse({"ok": True})
    pagamento = Pagamento.objects.filter(txid=result["txid"]).first()
    print("PAGAMENTO:", pagamento)
    if not pagamento:
        print("NÃO ENCONTROU PAGAMENTO COM TXID", result["txid"])
        return JsonResponse({"ok": True})
    print("STATUS:", pagamento.status)
    if pagamento.status == "pago":
        print("JÁ ESTAVA PAGO")
        return JsonResponse({"ok": True})
    if result.get("status") == "pago":
        print("VAI MARCAR COMO PAGO")
        pagamento.status = "pago"
        pagamento.payload = result.get("payload")
        pagamento.dt_pagamento = timezone.now()
        pagamento.save()
        print("SALVOU COM SUCESSO")
    return JsonResponse({"ok": True})