from datetime import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Fornecedor
from .forms import FornecedorForm
import unicodedata
from django.http import JsonResponse
from filiais.models import Usuario
from django.db.models.functions import Concat, Substr
from django.db.models import Q
from util.permissoes import verifica_permissao, verifica_alguma_permissao
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('fornecedores.view_fornecedor')
@login_required
def lista_fornecedores(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    f_s = request.GET.get('sit')
    t_pes = request.GET.get('t_pes')
    dt_ini = request.GET.get('dt_ini')
    dt_fim = request.GET.get('dt_fim')
    p_dt = request.GET.get('p_dt')
    reg = request.GET.get('reg', '10')
    # Lista de fornecedores filtrados
    empresa = request.user.empresa
    fornecedores = Fornecedor.objects.filter(vinc_emp=empresa)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        fornecedores = fornecedores.filter(fantasia__icontains=norm_s).order_by('fantasia')
    elif tp == 'cod' and s:
        try:
            fornecedores = fornecedores.filter(id__iexact=s).order_by('fantasia')
        except ValueError:
            fornecedores = Fornecedor.objects.none()
    if p_dt == 'Sim' and dt_ini and dt_fim:
        try:
            dt_ini_dt = datetime.strptime(dt_ini, '%d/%m/%Y').date()
            dt_fim_dt = datetime.strptime(dt_fim, '%d/%m/%Y').date()
            fornecedores = fornecedores.filter(dt_reg__range=(dt_ini_dt, dt_fim_dt))
        except ValueError:
            fornecedores = fornecedores.objects.none()
    if f_s in ['Ativo', 'Inativo']:
        fornecedores = fornecedores.filter(situacao=f_s).order_by('fantasia')
    if t_pes in ['Física', 'Jurídica']:
        fornecedores = fornecedores.filter(pessoa=t_pes).order_by('fantasia')
    if reg == 'todos':
        num_pagina = fornecedores.count() or 1  # Mostra todas as filials
    else:
        try:
            num_pagina = int(reg)
        except ValueError:
            num_pagina = 10
    paginator = Paginator(fornecedores, num_pagina)
    page = request.GET.get('page')
    fornecedores = paginator.get_page(page)
    return render(request, 'fornecedores/lista.html', {
        'fornecedores': fornecedores,
        's': s,
        'tp': tp,
        't_pes': t_pes,
        'dt_ini': dt_ini,
        'dt_fim': dt_fim,
        'p_dt': p_dt,
        'reg': reg
    })

@login_required
def lista_fornecedores_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit():
            condicao_busca = Q(fantasia__icontains=termo_busca) | Q(id=termo_busca)
        else:
            condicao_busca = Q(fantasia__icontains=termo_busca)
        fornecedores = Fornecedor.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{
            'id': fornecedor.id, 
            'text': f"{fornecedor.fantasia.upper()}",
            'situacao': fornecedor.situacao,
            'cpfCnpj': fornecedor.cpf_cnpj,
            'email': fornecedor.email,
            'tel': fornecedor.tel,
            'endereco': fornecedor.endereco,
            'cep': fornecedor.cep,
            'numero': fornecedor.numero,
            'bairro': fornecedor.bairro.nome_bairro if fornecedor.bairro else '',
            'cidade': fornecedor.cidade.nome_cidade if fornecedor.cidade else '',
            'uf': fornecedor.uf.nome_estado if fornecedor.uf else ''
            } for fornecedor in fornecedores]
        return JsonResponse({'results': results})
    except Exception as e:
        print(f"Erro na busca AJAX: {e}")
        return JsonResponse({'results': [], 'error': str(e)})

@login_required
def add_fornecedor(request):
    if not request.user.has_perm('fornecedores.add_fornecedor'):
        messages.info(request, 'Você não tem permissão para adicionar fornecedores.')
        return redirect('/fornecedores/lista/')
    if request.method == 'POST':
        form = FornecedorForm(request.POST, empresa=request.user.empresa)
        if form.is_valid():
            c = form.save(commit=False)
            bairro_id = request.POST.get('bairro')
            cidade_id = request.POST.get('cidade')
            estado_id = request.POST.get('uf')
            if bairro_id:
                try:
                    c.bairro = Bairro.objects.get(id=bairro_id)
                except Bairro.DoesNotExist:
                    c.bairro = None
            if cidade_id:
                try:
                    c.cidade = Cidade.objects.get(id=cidade_id)
                except Cidade.DoesNotExist:
                    c.cidade = None
            if estado_id:
                try:
                    c.uf = Estado.objects.get(id=estado_id)
                except Estado.DoesNotExist:
                    c.uf = None
            c.vinc_emp = request.user.empresa  # Busca a filial do usuário logado
            c.save()
            messages.success(request, 'Fornecedor adicionado com sucesso!')
            clie = str(c.id)
            return redirect('/fornecedores/lista/?tp=cod&s=' + clie)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'fornecedores/add.html', {'form': form, 'error_messages': error_messages})
    else: form = FornecedorForm(empresa=request.user.empresa)
    return render(request, 'fornecedores/add.html', {'form': form})

@verifica_alguma_permissao(
    'fornecedores.add_fornecedor',
    'fornecedores.change_fornecedor',
    'fornecedores.delete_fornecedor'
)
@login_required
def att_fornecedor(request, id):
    cli = get_object_or_404(Fornecedor, pk=id, vinc_emp=request.user.empresa)
    form = FornecedorForm(instance=cli, empresa=request.user.empresa)
    if not request.user.has_perm('fornecedores.change_fornecedor'):
        messages.info(request, 'Você não tem permissão para editar fornecedores.')
        return redirect('/fornecedores/lista/')
    if request.method == 'POST':
        form = FornecedorForm(request.POST, instance=cli, empresa=request.user.empresa)
        if form.is_valid():
            cli.save()
            next_url = request.POST.get('next') or request.GET.get('next')
            clie = str(cli.id)
            messages.success(request, 'Fornecedor atualizado com sucesso!')
            if next_url:
                return redirect(next_url)
            else:
                return redirect('/fornecedores/lista/?tp=cod&s=' + clie)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'fornecedores/att.html', {'form': form, 'cli': cli, 'error_messages': error_messages})
    else:
        form = FornecedorForm(instance=cli, empresa=request.user.empresa)
        return render(request, 'fornecedores/att.html', {'form': form, 'cli': cli})

@login_required
def del_fornecedor(request, id):
    if not request.user.has_perm('fornecedores.delete_fornecedor'):
        messages.info(request, 'Você não tem permissão para deletar fornecedores.')
        return redirect('/fornecedores/lista/')
    cli = get_object_or_404(Fornecedor, pk=id, vinc_emp=request.user.empresa)
    cli.delete()
    messages.success(request, 'Fornecedor deletado com sucesso!')
    return redirect('/fornecedores/lista/')