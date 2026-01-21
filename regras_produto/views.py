from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from produtos.models import Produto
from .models import RegraProduto
from .forms import RegraProdutoForm
import unicodedata
from django.http import JsonResponse
from filiais.models import Usuario
from util.permissoes import verifica_permissao
import json
from decimal import Decimal
from django.views.decorators.http import require_POST

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('regras_produto.view_regraproduto')
@login_required
def lista_regras(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    reg = request.GET.get('reg', '10')
    regras = RegraProduto.objects.filter(vinc_emp=request.user.empresa)

    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        regras = regras.filter(descricao__icontains=norm_s).order_by('descricao')
    elif tp == 'cod' and s:
        try:
            regras = regras.filter(id__iexact=s).order_by('descricao')
        except ValueError:
            regras = RegraProduto.objects.none()

    if reg == 'todos':
        num_pagina = regras.count() or 1
    else:
        try:
            num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError:
            num_pagina = 10  # Valor padrão

    paginator = Paginator(regras, num_pagina)
    page = request.GET.get('page')
    regras = paginator.get_page(page)

    return render(request, 'regras_produto/lista.html', {
        'regras': regras,
        's': s,
        'tp': tp,
        'reg': reg,
    })

@login_required
def lista_regras_ajax(request):
    term = request.GET.get('term', '')
    regras = RegraProduto.objects.filter(descricao__icontains=term)[:50]
    data = {
        'regras': [
            {
                'id': regra.id,
                'codigo': regra.codigo,
                'descricao': regra.descricao
            }
            for regra in regras
        ]
    }
    return JsonResponse(data)

@login_required
def regras_js(request):
    empresa = request.user.empresa
    if not empresa:
        return JsonResponse({}, status=403)
    regras = RegraProduto.objects.filter(
        vinc_emp=empresa,
        ativo=True
    ).values('codigo', 'tipo', 'expressao')
    data = {
        r['codigo']: {
            'tipo': r['tipo'],
            'expressao': r['expressao'],
        }
        for r in regras
    }
    return JsonResponse(data)

def aplicar_regra_selecao(regra, contexto):
    """
    Retorna o NOME ou CÓDIGO do produto selecionado
    """
    dados = json.loads(regra.expressao)

    # ========= MOTOR (por peso) =========
    if isinstance(dados, list):
        peso = contexto.get('peso', 0)
        for item in sorted(dados, key=lambda x: x['max']):
            if peso <= item['max']:
                return item['produto']

    # ========= MAPA DIRETO (lamina, pintura) =========
    if isinstance(dados, dict):
        # tenta chaves conhecidas
        for chave in contexto.values():
            if chave in dados:
                return dados[chave]

    return None

@require_POST
@login_required
def calcular_orcamento(request):
    empresa = request.user.empresa
    body = json.loads(request.body)

    contexto = body.get('contexto', {})
    produtos_req = body.get('produtos', [])

    produtos_base = (
        Produto.objects
        .select_related('regra')
        .filter(id__in=[p['id'] for p in produtos_req])
    )

    itens = []
    total_geral = Decimal('0.00')

    for prod in produtos_base:

        produto_final = prod
        qtd = Decimal('0')
        # ================= SELECAO =================
        if prod.regra and prod.regra.tipo == 'SELECAO':
            produto_nome = aplicar_regra_selecao(prod.regra, contexto)

            if produto_nome:
                produto_final = Produto.objects.get(
                    desc_prod=produto_nome,
                    vinc_emp=empresa
                )


        # ================= 2️⃣ QUANTIDADE =================
        if produto_final.regra and produto_final.regra.tipo == 'QTD':
            try:
                qtd = Decimal(str(eval(
                    produto_final.regra.expressao,
                    {},
                    contexto
                )))
            except Exception:
                qtd = Decimal('0')

        # ================= VALORES =================
        vl_unit = produto_final.preco_unitario()
        total = qtd * vl_unit
        total_geral += total

        itens.append({
            'id': produto_final.id,
            'desc': produto_final.desc_prod,
            'qtd': float(qtd),
            'vl_unit': float(vl_unit),
            'total': float(total),
            'regra_aplicada': produto_final.regra.codigo if produto_final.regra else None
        })

    return JsonResponse({
        'itens': itens,
        'total': float(total_geral)
    })

@login_required
def add_regra(request):
    if not request.user.has_perm('regras_produto.add_regraproduto'):
        messages.info(request, 'Você não tem permissão para adicionar regras de produto.')
        return redirect('/regras_produto/lista/')
    if request.method == 'POST':
        form = RegraProdutoForm(request.POST)
        if form.is_valid():
            e = form.save(commit=False)
            if request.user.is_authenticated:
                try:
                    e.vinc_emp = request.user.empresa  # Busca a filial do usuário logado
                except Usuario.DoesNotExist:
                    return JsonResponse({'error': 'Usuário não possui filial vinculada'}, status=400)
            e.save()
            messages.success(request, 'Regra adicionada com sucesso!')
            est = str(e.id)
            return redirect('/regras_produto/lista/?tp=cod&s=' + est)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'regras_produto/add.html', {'form': form, 'error_messages': error_messages})
    else: form = RegraProdutoForm()
    return render(request, 'regras_produto/add.html', {'form': form})

@login_required
def att_regra(request, id):
    e = get_object_or_404(RegraProduto, pk=id)
    form = RegraProdutoForm(instance=e)
    if not request.user.has_perm('regras_produto.change_regraproduto'):
        messages.info(request, 'Você não tem permissão para editar regras de produto.')
        return redirect('/regras_produto/lista/')
    if request.method == 'POST':
        form = RegraProdutoForm(request.POST, instance=e)
        if form.is_valid():
            e.save()
            est = str(e.id)
            messages.success(request, 'Regra atualizada com sucesso!')
            return redirect('/regras_produto/lista/?tp=cod&s=' + est)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'regras_produto/att.html', {'form': form, 'e': e, 'error_messages': error_messages})
    else:
        return render(request, 'regras_produto/att.html', {'form': form, 'e': e})

@login_required
def del_regra(request, id):
    if not request.user.has_perm('regras_produto.delete_regraproduto'):
        messages.info(request, 'Você não tem permissão para deletar regras de produto.')
        return redirect('/regras_produto/lista/')
    e = get_object_or_404(RegraProduto, pk=id)
    e.delete()
    messages.success(request, 'Regra deletada com sucesso!')
    return redirect('/regras_produto/lista/')