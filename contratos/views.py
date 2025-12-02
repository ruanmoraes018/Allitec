from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Contrato
from .forms import ContratoForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from filiais.models import Usuario
from django.db import DatabaseError, IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from empresas.models import Empresa
from datetime import datetime
from dateutil.relativedelta import relativedelta
from mensalidades.models import Mensalidade

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('contratos.view_contrato')
@login_required
def lista_contratos(request):
    emp = request.GET.get('emp')
    sit = request.GET.get('sit')
    dt_ini = request.GET.get('dt_ini')
    dt_fim = request.GET.get('dt_fim')
    por_dt = request.GET.get('p_dt')
    list_p = request.GET.get('list_p', 'dt_inicio')
    reg = request.GET.get('reg', '10')
    ordem = request.GET.get('ordem', 'empresa__fantasia')

    contratos = Contrato.objects.all().order_by(ordem)
    if sit in ['Ativo', 'Suspenso', 'Cancelado']:
        contratos = contratos.filter(situacao=sit)
    if por_dt == 'Sim' and dt_ini and dt_fim:
        try:
            # Converter as datas de entrada de string para date
            dt_ini_dt = datetime.strptime(dt_ini, '%d/%m/%Y').date()
            dt_fim_dt = datetime.strptime(dt_fim, '%d/%m/%Y').date()

            if list_p == 'dt_inicio':
                contratos = contratos.filter(dt_inicio__range=(dt_ini_dt, dt_fim_dt))
            elif list_p == 'dt_criacao':
                contratos = contratos.filter(created_at__range=(dt_ini_dt, dt_fim_dt))

        except ValueError:
            contratos = Contrato.objects.none()

    if reg == 'todos':
        num_pagina = contratos.count() or 1
    else:
        try:
            num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError:
            num_pagina = 10  # Valor padrão
    empresa_selecionada = None
    if emp:
        empresa_selecionada = Empresa.objects.filter(id=emp).first()

    # Se o cliente selecionado não for compatível com os filtros, removemos ele
        if empresa_selecionada:
            contratos = contratos.filter(empresa=empresa_selecionada)
            if (sit and empresa_selecionada.situacao != sit):
                empresa_selecionada = None  # Empresa não será incluído na lista

    empresas = Empresa.objects.all()

    paginator = Paginator(contratos, num_pagina)
    page = request.GET.get('page')
    contratos = paginator.get_page(page)

    return render(request, 'contratos/lista.html', {
        'contratos': contratos,
        'empresas': empresas,
        'emp': emp,
        'sit': sit,
        'dt_ini': dt_ini,
        'dt_fim': dt_fim,
        'p_dt': por_dt,
        'ordem': ordem,
        'reg': reg,
    })

@login_required
def lista_contratos_ajax(request):
    term = request.GET.get('term', '')
    contratos = Contrato.objects.filter(empresa__fantasia=term)[:10]
    data = {'contratos': [{'id': contrato.id, 'empresa': contrato.empresa.fantasia} for contrato in contratos]}
    return JsonResponse(data)

@login_required
def add_contrato(request):
    if not request.user.has_perm('contratos.add_contrato'):
        messages.info(request, 'Você não tem permissão para adicionar contratos.')
        return redirect('/contratos/lista/')
    error_messages = []
    if request.method == 'POST':
        form = ContratoForm(request.POST)
        if form.is_valid():
            try:
                contrato = form.save(commit=False)
                contrato.save()
                messages.success(request, 'Contrato gerado com sucesso!')
                return redirect('/contratos/lista/')
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
        form = ContratoForm()
    return render(request, 'contratos/add.html', {'form': form, 'error_messages': error_messages})

@login_required
def att_contrato(request, id):
    contrato = get_object_or_404(Contrato, pk=id)
    form = ContratoForm(instance=contrato)
    if not request.user.has_perm('contratos.change_contrato'):
        messages.info(request, 'Você não tem permissão para editar contratos.')
        return redirect('/contratos/lista/')
    if request.method == 'POST':
        form = ContratoForm(request.POST, instance=contrato)
        if form.is_valid():
            contrato.save()
            cid = str(contrato.id)
            messages.success(request, 'Contrato atualizado com sucesso!')
            return redirect('/contratos/lista/?tp=cod&s=' + cid)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'contratos/att.html', {'form': form, 'contrato': contrato, 'error_messages': error_messages})
    else:
        return render(request, 'contratos/att.html', {'form': form, 'contrato': contrato})

@login_required
def del_contrato(request, id):
    if not request.user.has_perm('contratos.delete_contrato'):
        messages.info(request, 'Você não tem permissão para deletar contratos.')
        return redirect('/contratos/lista/')
    contrato = get_object_or_404(Contrato, pk=id)
    contrato.delete()
    messages.success(request, 'Contrato deletado com sucesso!')
    return redirect('/contratos/lista/')

@login_required
def aprovar_contrato(request, id):
    contrato = get_object_or_404(Contrato, id=id)
    empresa = contrato.empresa
    empresa_id = contrato.empresa.id
    qtd_parcelas = contrato.qtd_parcelas
    vencimento = contrato.dt_inicio
    valor = contrato.valor_mensalidade
    contrato.status = "Aprovado"

    for i in range(1, qtd_parcelas + 1):
        gerar_vencimento = vencimento + relativedelta(months=i - 1)

        mensalidade = Mensalidade.objects.create(
            empresa=empresa,
            contrato=contrato,
            dt_venc=gerar_vencimento,
            vl_mens=valor,
            qtd_mens=qtd_parcelas,
            situacao='Aberta',
        )

        # Agora adiciona o num_mens
        mensalidade.num_mens = f'{contrato.id}-{empresa_id}/{i}-{qtd_parcelas}'
        mensalidade.save()
    contrato.save()
    cid = str(contrato.id)
    messages.success(request, 'Contrato Aprovado e Mensalidades geradas com sucesso!')
    return redirect('/contratos/lista/?tp=cod&s=' + cid)