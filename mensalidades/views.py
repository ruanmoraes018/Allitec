from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Mensalidade
from .forms import MensalidadeForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from filiais.models import Usuario
from django.db import DatabaseError, IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from empresas.models import Empresa
from datetime import datetime
from dateutil.relativedelta import relativedelta

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('mensalidades.view_mensalidade')
@login_required
def lista_mensalidades(request):
    emp = request.GET.get('emp')
    sit = request.GET.get('sit')
    dt_ini = request.GET.get('dt_ini')
    dt_fim = request.GET.get('dt_fim')
    por_dt = request.GET.get('p_dt')

    reg = request.GET.get('reg', '10')
    list_p = request.GET.get('list_p', 'dt_v')
    ordem = request.GET.get('ordem', 'empresa__fantasia')

    mensalidades = Mensalidade.objects.all().order_by(ordem)
    if sit in ['Aberta', 'Baixada']:
        mensalidades = mensalidades.filter(situacao=sit)
    if por_dt == 'Sim' and dt_ini and dt_fim:
        try:
            # Converter as datas de entrada de string para date
            dt_ini_dt = datetime.strptime(dt_ini, '%d/%m/%Y').date()
            dt_fim_dt = datetime.strptime(dt_fim, '%d/%m/%Y').date()

            if list_p == 'dt_v':
                mensalidades = mensalidades.filter(dt_venc__range=(dt_ini_dt, dt_fim_dt))
            elif list_p == 'dt_e':
                mensalidades = mensalidades.filter(created_at__range=(dt_ini_dt, dt_fim_dt))
            elif list_p == 'dt_p':
                mensalidades = mensalidades.filter(dt_pag__range=(dt_ini_dt, dt_fim_dt))

        except ValueError:
            mensalidades = Mensalidade.objects.none()

    if reg == 'todos':
        num_pagina = mensalidades.count() or 1
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
            mensalidades = mensalidades.filter(empresa=empresa_selecionada)
            if (sit and empresa_selecionada.situacao != sit):
                empresa_selecionada = None  # Empresa não será incluído na lista

    empresas = Empresa.objects.all()
    paginator = Paginator(mensalidades, num_pagina)
    page = request.GET.get('page')
    mensalidades = paginator.get_page(page)

    return render(request, 'mensalidades/lista.html', {
        'mensalidades': mensalidades,
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
def lista_mensalidades_ajax(request):
    term = request.GET.get('term', '')
    mensalidades = Mensalidade.objects.filter(empresa__fantasia=term)[:10]
    data = {'mensalidades': [{'id': mensalidade.id, 'empresa': mensalidade.empresa.fantasia} for mensalidade in mensalidades]}
    return JsonResponse(data)

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
                mensalidade_base = form.save(commit=False)

                qtd_parcelas = mensalidade_base.qtd_mens
                vencimento = mensalidade_base.dt_venc
                valor = mensalidade_base.vl_mens
                empresa = mensalidade_base.empresa
                tp_mens = mensalidade_base.tp_mens
                obs = mensalidade_base.obs
                empresa_id = empresa.id

                for i in range(1, qtd_parcelas + 1):
                    gerar_vencimento = vencimento + relativedelta(months=i - 1)

                    # Criar e salvar a mensalidade para obter o ID
                    nova_mensalidade = Mensalidade.objects.create(
                        dt_venc=gerar_vencimento,
                        vl_mens=valor,
                        situacao='Aberta',
                        tp_mens=tp_mens,
                        qtd_mens=1,
                        obs=obs,
                        empresa=empresa
                    )

                    # Agora atualizar o num_mens com o id da mensalidade
                    nova_mensalidade.num_mens = f'{nova_mensalidade.id}-{empresa_id}/{i}-{qtd_parcelas}'
                    nova_mensalidade.save()

                if qtd_parcelas > 1:
                    messages.success(request, 'Mensalidades geradas com sucesso!')
                else:
                    messages.success(request, 'Mensalidade gerada com sucesso!')

                return redirect('/mensalidades/lista/')

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
            cid = str(mensalidade.id)
            messages.success(request, 'Mensalidade atualizada com sucesso!')
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