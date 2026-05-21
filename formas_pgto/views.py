import json
from django.forms import ValidationError
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import FormaPgto
from .forms import FormaPgtoForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from filiais.models import Usuario
from django.db.models import Q
from django.db import IntegrityError, DatabaseError, transaction
from django.core.exceptions import ObjectDoesNotExist

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('formas_pgto.view_formapgto')
@login_required
def lista_formas_pgto(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')
    empresa = request.user.empresa
    formas_pgto = FormaPgto.objects.filter(vinc_emp=empresa)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        formas_pgto = formas_pgto.filter(descricao__icontains=norm_s).order_by('descricao')
    elif tp == 'cod' and s:
        try: formas_pgto = formas_pgto.filter(codigo__iexact=s).order_by('descricao')
        except ValueError: formas_pgto = FormaPgto.objects.none()
    if reg == 'todos': num_pagina = formas_pgto.count() or 1
    else:
        try: num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError: num_pagina = 10  # Valor padrão
    paginator = Paginator(formas_pgto, num_pagina)
    page = request.GET.get('page')
    formas_pgto = paginator.get_page(page)
    return render(request, 'formas_pgto/lista.html', {'formas_pgto': formas_pgto, 's': s, 'tp': tp, 'reg': reg,})

def forma_padrao(request):
    fp = FormaPgto.objects.filter(vinc_emp=request.user.empresa, situacao='Ativo', forma_padrao='Sim').first()
    if not fp: return JsonResponse({'id': None})
    return JsonResponse({'id': fp.codigo, 'text': fp.descricao})

@login_required
def lista_formas_pgto_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit(): condicao_busca = Q(descricao__icontains=termo_busca) | Q(codigo=termo_busca)
        else: condicao_busca = Q(descricao__icontains=termo_busca)
        formas_pgto = FormaPgto.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': forma_pgto.codigo, 'text': f"{forma_pgto.descricao.upper()}"} for forma_pgto in formas_pgto]
        return JsonResponse({'results': results})
    except Exception as e:
        return JsonResponse({'results': [], 'error': str(e)})

@login_required
def forma_pgto_info(request, codigo):
    fp = get_object_or_404(FormaPgto, codigo=codigo, vinc_emp=request.user.empresa)
    return JsonResponse({"id":fp.codigo,"descricao":fp.descricao,"gera_parcelas":fp.gera_parcelas,"troco":fp.troco == "Sim","gateway":fp.gateway,"credenciais":fp.credenciais,'tipo': fp.tipo,})

@login_required
def get_forma_pgto(request):
    forma_id = request.GET.get("id")
    try:
        forma = FormaPgto.objects.get(codigo=forma_id, vinc_emp=request.user.empresa)
        return JsonResponse({"id": forma.codigo, "descricao": forma.descricao})
    except FormaPgto.DoesNotExist: return JsonResponse({"error": "Forma não encontrada"}, status=404)

@login_required
def add_formas_pgto(request):
    error_messages = []
    if not request.user.has_perm('formas_pgto.add_formapgto'):
        messages.info(request, 'Você não tem permissão para adicionar formas de pagamento.')
        return redirect('/formas_pgto/lista/')
    try:
        if request.method == 'POST':
            form = FormaPgtoForm(request.POST, request.FILES)
            if not form.is_valid():
                # 1. Pega erros dos campos
                error_messages = [f"Campo ({field.label}) é obrigatório!" for field in form if field.errors]

                # 🔥 CORREÇÃO: Pega também os erros globais (como os do clean)
                for err in form.non_field_errors():
                    error_messages.append(f"<i class='fa-solid fa-xmark'></i> {err}")

                return render(request, 'formas_pgto/add.html', {'form': form, 'error_messages': error_messages})

            c = form.save(commit=False)
            c.vinc_emp = request.user.empresa
            c.save()
            messages.success(request, 'Forma de Pagamento adicionada com sucesso!')
            cid = str(c.codigo)
            return redirect('/formas_pgto/lista/?tp=cod&s=' + cid)
        form = FormaPgtoForm()
    except ObjectDoesNotExist: error_messages.append("<i class='fa-solid fa-xmark'></i> Objeto não encontrado!")
    except IntegrityError as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {str(e)}")
    except DatabaseError as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco de dados: {str(e)}")
    except Exception as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    return render(request, 'formas_pgto/add.html', {'form': form})

@login_required
def att_formas_pgto(request, codigo):
    error_messages = []
    c = get_object_or_404(FormaPgto, codigo=codigo, vinc_emp=request.user.empresa)
    if not request.user.has_perm('formas_pgto.change_formapgto'):
        messages.info(request, 'Você não tem permissão para editar formas de pagamento.')
        return redirect('/formas_pgto/lista/')
    if request.method == 'POST':
        form = FormaPgtoForm(request.POST, request.FILES, instance=c)
        try:
            if form.is_valid():
                c = form.save()  # 🔥 ESSENCIAL (salva credenciais corretamente)
                next_url = request.POST.get('next') or request.GET.get('next')
                cid = str(c.codigo)
                messages.success(request, 'Forma de Pagamento atualizada com sucesso!')
                if next_url: return redirect(next_url)
                else: return redirect(f'/formas_pgto/lista/?tp=cod&s={cid}')
            else:
                # erros de campo
                for field in form:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> {field.label}: {error}")
        except ValidationError as e:
            # erros do clean()
            if hasattr(e, 'messages'):
                for msg in e.messages:
                    error_messages.append(f"<i class='fa-solid fa-xmark'></i> {msg}")
            else: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de validação.")
        except IntegrityError as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de integridade: {str(e)}")
        except DatabaseError as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro de banco de dados: {str(e)}")
        except Exception as e: error_messages.append(f"<i class='fa-solid fa-xmark'></i> Erro inesperado: {str(e)}")
    else:
        form = FormaPgtoForm(instance=c)
        form.initial['credenciais'] = json.dumps(form.initial.get('credenciais', {}))
    return render(request, 'formas_pgto/att.html', {'form': form, 'c': c, 'error_messages': error_messages})

@login_required
def del_formas_pgto(request, codigo):
    if not request.user.has_perm('formas_pgto.delete_formapgto'):
        messages.info(request, 'Você não tem permissão para deletar formas de pagamento.')
        return redirect('/formas_pgto/lista/')
    c = get_object_or_404(FormaPgto, codigo=codigo, vinc_emp=request.user.empresa)
    c.delete()
    messages.success(request, 'Forma de Pagamento deletada com sucesso!')
    return redirect('/formas_pgto/lista/')