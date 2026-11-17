from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Proposta
from .forms import PropostaForm
from util.logo_impressao import img_base64
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
import locale
from django.template.loader import render_to_string
from weasyprint import HTML
from django.contrib.staticfiles import finders
from django.utils import timezone
from django.db import DatabaseError, IntegrityError, transaction

@login_required
def lista_propostas(request):
    search = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')
    sit = request.GET.get('sit')
    propostas = Proposta.objects.all().order_by('nome_emp')
    if sit in ['Aberta', 'Confirmada']:
        propostas = propostas.filter(situacao=sit)
    if search:
        if tp == 'desc':
            propostas = propostas.filter(nome_emp__icontains=search)
        else:
            propostas = propostas.filter(id__icontains=search)
    if reg == 'todas':
        num_pagina = propostas.count() or 1
    else:
        try:
            num_pagina = int(reg)
        except ValueError:
            num_pagina = 10
    paginator = Paginator(propostas, num_pagina)
    page = request.GET.get('page')
    propostas = paginator.get_page(page)
    prop_ab_pg = sum(1 for p in propostas.object_list if p.situacao == 'Aberta')
    prop_conf_pg = sum(1 for p in propostas.object_list if p.situacao == 'Confirmada')
    return render(request, 'propostas/lista.html',{
        'propostas': propostas, 's': search, 'tp': tp,
        'sit': sit, 'reg': reg, 'prop_ab': prop_ab_pg, 'prop_conf': prop_conf_pg,
    })

@login_required
def adicionar_proposta(request):
    error_messages = []
    if request.method != 'POST':
        form = PropostaForm()
        return render(request, 'propostas/add.html', {'form': form, 'error_messages': error_messages})
    form = PropostaForm(request.POST)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'propostas/add.html', {'form': form, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            p = form.save(commit=False)
            p.situacao = "Aberta"
            p.dt_emi = timezone.now()
            p.save()
            messages.success(request, 'Proposta adicionada com sucesso!')
            return redirect('/propostas/lista/?tp=cod&s=' + str(p.id))
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
    return render(request, 'propostas/add.html', {'form': form, 'error_messages': error_messages})

@login_required
def atualizar_proposta(request, id):
    error_messages = []
    p = get_object_or_404(Proposta, pk=id)
    if request.method != 'POST':
        form = PropostaForm(instance=p)
        return render(request, 'propostas/att.html', {'form': form, 'proposta': p, 'error_messages': error_messages})
    form = PropostaForm(request.POST, instance=p)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'propostas/att.html', {'form': form, 'proposta': p, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            p = form.save()
            messages.success(request, 'Proposta atualizada com sucesso!')
            return redirect('/propostas/lista/?tp=cod&s=' + str(p.id))
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
    return render(request, 'propostas/att.html', {'form': form, 'proposta': p, 'error_messages': error_messages})

@login_required
def deletar_proposta(request, id):
    p = get_object_or_404(Proposta, pk=id)
    try:
        with transaction.atomic():
            if p.situacao == 'Aberta':
                p.delete()
                messages.success(request, 'Proposta deletada com sucesso!')
                return redirect('/propostas/lista/')
            else:
                messages.warning(request, 'Propostas confirmadas não podem ser deletadas!')
                return redirect('/propostas/lista/?s=' + str(p.id))
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
    return redirect('/propostas/lista/')

@login_required
def mudar_situacao(request, id):
    p = get_object_or_404(Proposta, pk=id)
    try:
        with transaction.atomic():
            if(p.situacao == 'Aberta'):
                p.situacao = 'Confirmada'
            p.data_confirmacao = timezone.now()
            p.save()
            messages.success(request, 'Proposta Aceita com Sucesso! Realize o registro do contrato da empresa!')
            return redirect('/propostas/lista/?tp=cod&s=' + str(p.id))
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
    return redirect('/propostas/lista/?tp=cod&s=' + str(p.id))

@login_required
def pdf_prop_html(request, id):
    p = Proposta.objects.get(pk=id)
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    dt_format = p.dt_emi.strftime('%d de %B de %Y').upper()
    logo_allitec = finders.find('img/Allitec.png')
    print(logo_allitec)
    lg_allitec = img_base64(logo_allitec)
    print(lg_allitec[:50])
    html = render_to_string('propostas/pdf_proposta.html', {'p': p, 'lg_allitec': lg_allitec, 'dt_format': dt_format})
    pdf = HTML(string=html).write_pdf()
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = ( f'inline; filename="PROPOSTA DE SISTEMA - {p.nome_emp}.pdf"' )
    return response