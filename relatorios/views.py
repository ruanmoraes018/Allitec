from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from filiais.models import Filial
from .config import RELATORIOS
from datetime import datetime
from django.template.loader import render_to_string
from weasyprint import HTML, CSS
from django.db.models import (
    Sum,
    F,
    DecimalField,
    Count,
    Avg, ExpressionWrapper
)
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from decimal import Decimal
from pedidos.models import Pedido, PedidoProduto

def parse_date_br(date_str):
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return None

@login_required
def lista_relatorios(request):
    relatorios = [
        rel for rel in RELATORIOS
        if request.user.has_perm(rel['perm'])
    ]
    return render( request, 'relatorios/lista.html', {'relatorios': relatorios})

@login_required
def relatorio_pedidos(request):
    pedidos = (Pedido.objects.filter(vinc_emp=request.user.empresa).select_related('cli', 'vendedor', 'vinc_fil').prefetch_related('itens__produto', 'formas_pgto__forma_pgto') .order_by('id'))
    # FILTROS
    tipo = request.GET.get('tipo', 'resumido')
    dt_ini = request.GET.get('dt_ini')
    dt_fim = request.GET.get('dt_fim')
    cli = request.GET.get('cl')
    fil = request.GET.get('fil')
    vend = request.GET.get('vend_r_ped')
    filial = None
    if dt_ini:
        dt_ini = parse_date_br(dt_ini)
        if dt_ini: pedidos = pedidos.filter(dt_emi__date__gte=dt_ini)
    if dt_fim:
        dt_fim = parse_date_br(dt_fim)
        if dt_fim: pedidos = pedidos.filter(dt_emi__date__lte=dt_fim)
    if cli: pedidos = pedidos.filter(cli_id=cli)
    # Filtro por Filial
    if fil: 
        pedidos = pedidos.filter(vinc_fil_id=fil)
        filial = Filial.objects.filter(id=fil, vinc_emp=request.user.empresa).first()
    # Filtro por Vendedor
    if vend: pedidos = pedidos.filter(vendedor_id=vend)
    pedidos = pedidos.filter(situacao='Faturado')
    total_pedidos = pedidos.count()
    valor_total = pedidos.aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    context = {'pedidos': pedidos, 'tipo': tipo, 'dt_ini': dt_ini, 'dt_fim': dt_fim, 'fil': filial, 'total_pedidos': total_pedidos, 'valor_total': valor_total,}
    html_string = render_to_string('relatorios/pedidos.html', context, request=request)
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(
        stylesheets=[
            CSS(string="""
                @page {
                    size: A4 landscape; margin: 10mm;
                    @bottom-right { content: "Página " counter(page) " de " counter(pages); font-size: 10px; font-weight: bold; }
                    @bottom-left { content: "By Allitec Sistemas"; font-size: 10px; font-weight: bold; font-style: italic; }
                }
                body {font-family: Arial, sans-serif; font-size: 11px; color: #222;}
                h1 {margin-bottom: 5px;}
                .titulo {text-align: center;}
                .subtitulo {margin-bottom: 20px; color: #666; font-weight: bold;}
                .pedido-box {border: 1px solid #cfcfcf; margin-bottom: 20px;  padding: 10px; border-radius: 5px;}
                .pedido-header {background: #f2f2f2; padding: 8px; margin-bottom: 10px; font-weight: bold;}
                table {width: 100%; border-collapse: collapse; margin-top: 10px;}
                th {background: #f2f2f2;}
                th, td {border: 1px solid #ccc; padding: 5px;}
                .right {text-align: right;}
                .center {text-align: center;}
                .total-geral {margin-top: 20px; font-size: 14px; font-weight: bold; float: right;}
                .total-pedidos {margin-top: 20px; font-size: 14px; font-weight: bold; float: left;}
                .situacao { color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold;}
                .fat {background: #3CB371;}
                .abe {background: #005eff;}
                .can {background: #B22222;}
            """)
        ]
    )
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = ('inline; filename="relatorio_pedidos.pdf"')
    return response

@login_required
def relatorio_produtos_vendidos(request):
    tipo = request.GET.get('tipo_v_p', 'resumido')
    dt_ini = request.GET.get('dt_ini_v_p')
    dt_fim = request.GET.get('dt_fim_v_p')
    grupo = request.GET.get('grupo')
    marca = request.GET.get('marca')
    vendedor = request.GET.get('vend')
    ordenacao = request.GET.get('ordenacao', 'valor')
    # CONVERTE DATAS
    if dt_ini: dt_ini = datetime.strptime(dt_ini, '%d/%m/%Y').date()
    if dt_fim: dt_fim = datetime.strptime(dt_fim,'%d/%m/%Y').date()
    itens = PedidoProduto.objects.filter(
        pedido__vinc_emp=request.user.empresa,
        pedido__situacao='Faturado'
    ).only('produto', 'quantidade', 'vl_unit', 'pedido')
    # FILTROS
    if dt_ini: itens = itens.filter(pedido__dt_fat__date__gte=dt_ini)
    if dt_fim: itens = itens.filter(pedido__dt_fat__date__lte=dt_fim)
    if grupo: itens = itens.filter(produto__grupo_id=grupo)
    if marca: itens = itens.filter(produto__marca_id=marca)
    if vendedor: itens = itens.filter(pedido__vendedor_id=vendedor)
    # AGRUPAMENTO
    produtos = (itens.values('produto__id', 'produto__desc_prod', 'produto__grupo__nome_grupo', 'produto__marca__nome_marca', 'produto__estoque_prod', 'produto__vl_compra',)
        .annotate(
            qtd_vendida=Coalesce(Sum('quantidade'), Decimal('0.00')), total_vendido=Coalesce(Sum(F('quantidade') * F('vl_unit'), output_field=DecimalField()), Decimal('0.00')),
            total_compras=Coalesce(Sum(F('quantidade') * F('produto__vl_compra'), output_field=DecimalField()), Decimal('0.00')),
            lucro=ExpressionWrapper(
                Coalesce(Sum(F('quantidade') * F('vl_unit'), output_field=DecimalField()), Decimal('0.00')) -
                Coalesce(Sum(F('quantidade') * F('produto__vl_compra'), output_field=DecimalField()), Decimal('0.00')), output_field=DecimalField()),
            margem_lucro=ExpressionWrapper(((
                    Coalesce(Sum(F('quantidade') * F('vl_unit'), output_field=DecimalField()), Decimal('0.00')) -
                    Coalesce(Sum(F('quantidade') * F('produto__vl_compra'), output_field=DecimalField()), Decimal('0.00'))) * Decimal('100.00')) /
                    Coalesce(Sum(F('quantidade') * F('produto__vl_compra'), output_field=DecimalField()), Decimal('1.00')), output_field=DecimalField( max_digits=10, decimal_places=2)
            ),
            total_pedidos=Count('pedido_id', distinct=True), valor_medio=Coalesce(Sum(F('quantidade') * F('vl_unit'), output_field=DecimalField()) / Count('id'), Decimal('0.00')),
        )
    )
    # ORDENAÇÃO
    if ordenacao == 'qtd': produtos = produtos.order_by('-qtd_vendida')
    elif ordenacao == 'descricao': produtos = produtos.order_by('produto__desc_prod')
    else: produtos = produtos.order_by('-total_vendido')
    # TOTAIS
    total_vendido = produtos.aggregate(
        total=Coalesce(
            Sum('total_vendido'),
            Decimal('0.00')
        )
    )['total']
    total_compras = produtos.aggregate(
        total=Coalesce(
            Sum('total_compras'),
            Decimal('0.00')
        )
    )['total']
    lucro_total = total_vendido - total_compras
    total_qtd = produtos.aggregate(total=Coalesce(Sum('qtd_vendida'), Decimal('0.00')))['total']
    total_produtos = produtos.count()
    produto_campeao = produtos.first()
    context = {
        'produtos': produtos, 'tipo': tipo, 'dt_ini': dt_ini, 'dt_fim': dt_fim, 'total_vendido': total_vendido, 'total_qtd': total_qtd, 'total_produtos': total_produtos, 
        'produto_campeao': produto_campeao, 'total_compras': total_compras, 'lucro_total': lucro_total,
    }
    html_string = render_to_string('relatorios/vendas_produtos.html', context, request=request)
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(
        stylesheets=[
            CSS(
                string="""
                    @page {
                        size: A4 landscape; margin: 10mm;
                        @bottom-right { content: "Página " counter(page) " de " counter(pages); font-size: 10px; font-weight: bold; }
                        @bottom-left { content: "By Allitec Sistemas"; font-size: 10px; font-weight: bold; font-style: italic; }
                    }
                    body {
                        font-family: Arial, sans-serif; font-size: 10px; color: #222;
                    }
                    h1 {
                        text-align: center; margin-bottom: 2px;
                    }
                    .subtitulo {
                        margin-bottom: 20px; color: #666; font-weight: bold;
                    }
                    .cards {
                        width: 100%; margin-bottom: 20px;
                    }
                    .card {
                        width: 24%; display: inline-block; border: 1px solid #ccc; border-radius: 5px; padding: 10px; margin-right: 1%; vertical-align: top; box-sizing: border-box;
                    }
                    .card-titulo {
                        font-size: 11px; color: #666;
                    }
                    .card-valor {
                        font-size: 16px; font-weight: bold; margin-top: 5px;
                    }
                    table {
                        width: 100%; border-collapse: collapse;
                    }
                    th {
                        background: #f2f2f2;
                    }
                    th, td {
                        border: 1px solid #ccc; padding: 5px;
                    }
                    .right {
                        text-align: right;
                    }
                    .center {
                        text-align: center;
                    }
                    .total-geral {
                        margin-top: 20px; font-size: 14px; font-weight: bold; float: right;
                    }
                    .total-produtos {
                        margin-top: 20px; font-size: 14px; font-weight: bold; float: left;
                    }
                """
            )
        ]
    )
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = ('inline; filename="produtos_vendidos.pdf"')
    return response