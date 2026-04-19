from datetime import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Vendedor
from .forms import VendedorForm
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

@verifica_permissao('vendedores.view_vendedor')
@login_required
def lista_vendedores(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    f_s = request.GET.get('sit')
    t_pes = request.GET.get('t_pes')
    dt_ini = request.GET.get('dt_ini')
    dt_fim = request.GET.get('dt_fim')
    p_dt = request.GET.get('p_dt')
    reg = request.GET.get('reg', '10')
    # Lista de vendedores filtrados
    empresa = request.user.empresa
    vendedores = Vendedor.objects.filter(vinc_emp=empresa)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        vendedores = vendedores.filter(fantasia__icontains=norm_s).order_by('fantasia')
    elif tp == 'cod' and s:
        try:
            vendedores = vendedores.filter(id__iexact=s).order_by('fantasia')
        except ValueError:
            vendedores = Vendedor.objects.none()
    if p_dt == 'Sim' and dt_ini and dt_fim:
        try:
            dt_ini_dt = datetime.strptime(dt_ini, '%d/%m/%Y').date()
            dt_fim_dt = datetime.strptime(dt_fim, '%d/%m/%Y').date()
            vendedores = vendedores.filter(dt_reg__range=(dt_ini_dt, dt_fim_dt))
        except ValueError:
            vendedores = vendedores.objects.none()
    if f_s in ['Ativo', 'Inativo']:
        vendedores = vendedores.filter(situacao=f_s).order_by('fantasia')
    if t_pes in ['Física', 'Jurídica']:
        vendedores = vendedores.filter(pessoa=t_pes).order_by('fantasia')
    if reg == 'todos':
        num_pagina = vendedores.count() or 1  # Mostra todas as filials
    else:
        try:
            num_pagina = int(reg)
        except ValueError:
            num_pagina = 10
    paginator = Paginator(vendedores, num_pagina)
    page = request.GET.get('page')
    vendedores = paginator.get_page(page)
    return render(request, 'vendedores/lista.html', {
        'vendedores': vendedores,
        's': s,
        'tp': tp,
        't_pes': t_pes,
        'dt_ini': dt_ini,
        'dt_fim': dt_fim,
        'p_dt': p_dt,
        'reg': reg
    })

@login_required
def lista_vendedores_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit():
            condicao_busca = Q(fantasia__icontains=termo_busca) | Q(id=termo_busca)
        else:
            condicao_busca = Q(fantasia__icontains=termo_busca)
        vendedores = Vendedor.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{
            'id': vendedor.id,
            'text': f"{vendedor.fantasia.upper()}",
            'situacao': vendedor.situacao,
            'cpfCnpj': vendedor.cpf_cnpj,
            'email': vendedor.email,
            'tel': vendedor.tel,
            'endereco': vendedor.endereco,
            'cep': vendedor.cep,
            'numero': vendedor.numero,
            'bairro': vendedor.bairro.nome_bairro if vendedor.bairro else '',
            'cidade': vendedor.cidade.nome_cidade if vendedor.cidade else '',
            'uf': vendedor.uf.nome_estado if vendedor.uf else ''
            } for vendedor in vendedores]
        return JsonResponse({'results': results})
    except Exception as e:
        print(f"Erro na busca AJAX: {e}")
        return JsonResponse({'results': [], 'error': str(e)})

@login_required
def add_vendedor(request):
    if not request.user.has_perm('vendedores.add_vendedor'):
        messages.info(request, 'Você não tem permissão para adicionar vendedores.')
        return redirect('/vendedores/lista/')
    if request.method == 'POST':
        form = VendedorForm(request.POST, empresa=request.user.empresa)
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
            messages.success(request, 'Vendedor adicionado com sucesso!')
            clie = str(c.id)
            return redirect('/vendedores/lista/?tp=cod&s=' + clie)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'vendedores/add.html', {'form': form, 'error_messages': error_messages})
    else: form = VendedorForm(empresa=request.user.empresa)
    return render(request, 'vendedores/add.html', {'form': form})

@verifica_alguma_permissao(
    'vendedores.add_vendedor',
    'vendedores.change_vendedor',
    'vendedores.delete_vendedor'
)
@login_required
def att_vendedor(request, id):
    cli = get_object_or_404(Vendedor, pk=id, vinc_emp=request.user.empresa)
    form = VendedorForm(instance=cli, empresa=request.user.empresa)
    if not request.user.has_perm('vendedores.change_vendedor'):
        messages.info(request, 'Você não tem permissão para editar vendedores.')
        return redirect('/vendedores/lista/')
    if request.method == 'POST':
        form = VendedorForm(request.POST, instance=cli, empresa=request.user.empresa)
        if form.is_valid():
            cli.save()
            next_url = request.POST.get('next') or request.GET.get('next')
            clie = str(cli.id)
            messages.success(request, 'Vendedor atualizado com sucesso!')
            if next_url:
                return redirect(next_url)
            else:
                return redirect('/vendedores/lista/?tp=cod&s=' + clie)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'vendedores/att.html', {'form': form, 'cli': cli, 'error_messages': error_messages})
    else:
        form = VendedorForm(instance=cli, empresa=request.user.empresa)
        return render(request, 'vendedores/att.html', {'form': form, 'cli': cli})

@login_required
def del_vendedor(request, id):
    if not request.user.has_perm('vendedores.delete_vendedor'):
        messages.info(request, 'Você não tem permissão para deletar vendedores.')
        return redirect('/vendedores/lista/')
    cli = get_object_or_404(Vendedor, pk=id, vinc_emp=request.user.empresa)
    cli.delete()
    messages.success(request, 'Vendedor deletado com sucesso!')
    return redirect('/vendedores/lista/')