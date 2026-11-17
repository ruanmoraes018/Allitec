from datetime import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Tecnico
from .forms import TecnicoForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from django.db.models import Q
from util.logs import gerar_alteracoes, registrar_log
from django.db import DatabaseError, IntegrityError, transaction
from django.core.exceptions import ObjectDoesNotExist

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('tecnicos.view_tecnico')
@login_required
def lista_tecnicos(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    f_s = request.GET.get('sit')
    dt_ini = request.GET.get('dt_ini')
    dt_fim = request.GET.get('dt_fim')
    p_dt = request.GET.get('p_dt')
    reg = request.GET.get('reg', '10')
    empresa=request.user.empresa
    tecnicos = Tecnico.objects.filter(vinc_emp=empresa)
    if tp == 'nome' and s:
        norm_s = remove_accents(s).lower()
        tecnicos = tecnicos.filter(nome__icontains=norm_s).order_by('nome')
    elif tp == 'cod' and s:
        try: tecnicos = tecnicos.filter(codigo__iexact=s).order_by('nome')
        except ValueError: tecnicos = Tecnico.objects.none()
    if p_dt == 'Sim' and dt_ini and dt_fim:
        try:
            dt_ini_dt = datetime.strptime(dt_ini, '%d/%m/%Y').date()
            dt_fim_dt = datetime.strptime(dt_fim, '%d/%m/%Y').date()
            tecnicos = tecnicos.filter(dt_reg__range=(dt_ini_dt, dt_fim_dt))
        except ValueError: tecnicos = Tecnico.objects.none()
    if f_s in ['Ativo', 'Inativo']: tecnicos = tecnicos.filter(situacao=f_s).order_by('nome')
    if reg == 'todos': num_pagina = tecnicos.count() or 1  # Mostra todas as filials
    else:
        try: num_pagina = int(reg)
        except ValueError: num_pagina = 10
    paginator = Paginator(tecnicos, num_pagina)
    page = request.GET.get('page')
    tecnicos = paginator.get_page(page)
    return render(request, 'tecnicos/lista.html', {'tecnicos': tecnicos, 's': s, 'tp': tp, 'dt_ini': dt_ini, 'dt_fim': dt_fim, 'p_dt': p_dt, 'reg': reg,})

@login_required
def lista_tecnicos_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit(): condicao_busca = Q(nome__icontains=termo_busca) | Q(codigo=termo_busca)
        else: condicao_busca = Q(nome__icontains=termo_busca)
        tecnicos = Tecnico.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': tecnico.codigo, 'text': f"{tecnico.nome.upper()}"} for tecnico in tecnicos]
        return JsonResponse({'results': results})
    except Exception as e: return JsonResponse({'results': [], 'error': str(e)})

@login_required
def add_tecnico(request):
    error_messages = []
    empresa = request.user.empresa
    if not request.user.has_perm('tecnicos.add_tecnico'):
        messages.info(request, 'Você não tem permissão para adicionar técnicos.')
        return redirect('/tecnicos/lista/')
    if request.method != 'POST':
        form = TecnicoForm(empresa=empresa)
        return render(request, 'tecnicos/add-tecnico.html', {'form': form, 'error_messages': error_messages})
    form = TecnicoForm(data=request.POST, empresa=empresa)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'tecnicos/add-tecnico.html', {'form': form, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            t = form.save(commit=False)
            t.vinc_emp = empresa
            t.save()
            registrar_log(request, "CRIAR", "Técnico", t.nome, f"Adicionou o técnico: {t.codigo} - {t.nome}", t.id, gerar_alteracoes(obj_novo=t))
            messages.success(request, 'Técnico adicionado com sucesso!')
            tec = str(t.codigo)
            return redirect('/tecnicos/lista/?tp=cod&s=' + tec)
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
    return render(request, 'tecnicos/add-tecnico.html', {'form': form, 'error_messages': error_messages})

@login_required
def att_tecnico(request, codigo):
    error_messages = []
    empresa = request.user.empresa
    tec = get_object_or_404(Tecnico, codigo=codigo, vinc_emp=empresa)
    it_old = Tecnico.objects.get(codigo=tec.codigo, vinc_emp=empresa)
    if not request.user.has_perm('tecnicos.change_tecnico'):
        messages.info(request, 'Você não tem permissão para editar técnicos.')
        return redirect('/tecnicos/lista/')
    if request.method != 'POST':
        form = TecnicoForm(instance=tec, empresa=empresa)
        return render(request, 'tecnicos/att-tecnico.html', {'form': form, 'tec': tec, 'error_messages': error_messages})
    form = TecnicoForm(data=request.POST, instance=tec, empresa=empresa)
    if not form.is_valid():
        for field in form:
            for error in field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}): {error}")
        return render(request, 'tecnicos/att-tecnico.html', {'form': form, 'tec': tec, 'error_messages': error_messages})
    try:
        with transaction.atomic():
            tec = form.save()
            registrar_log(request, "ALTERAR", "Técnico", tec.nome, f"Alterou o técnico: {tec.codigo} - {tec.nome}", tec.id, gerar_alteracoes(it_old, tec))
            t = str(tec.codigo)
            messages.success(request, 'Técnico atualizado com sucesso!')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url: return redirect(next_url)
            else: return redirect('/tecnicos/lista/?tp=cod&s=' + t)
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
    return render(request, 'tecnicos/att-tecnico.html', {'form': form, 'tec': tec, 'error_messages': error_messages})

@login_required
def del_tecnico(request, codigo):
    if not request.user.has_perm('tecnicos.delete_tecnico'):
        messages.info(request, 'Você não tem permissão para deletar técnicos.')
        return redirect('/tecnicos/lista/')
    try:
        with transaction.atomic():
            tec = get_object_or_404(Tecnico, codigo=codigo, vinc_emp=request.user.empresa)
            registrar_log(request, "EXCLUIR", "Técnico", tec.nome,f"Excluiu o técnico: {tec.codigo} - {tec.nome}",tec.id, gerar_alteracoes(obj_antigo=tec))
            tec.delete()
            messages.success(request, 'Técnico deletado com sucesso!')
            return redirect('/tecnicos/lista/')
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
    return redirect('/tecnicos/lista/')