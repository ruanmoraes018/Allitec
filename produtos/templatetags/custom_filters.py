from django import template
from produtos.models import ProdutoTabela

register = template.Library()

@register.filter
def moeda_br(value):
    try:
        valor = float(value)
        return "{:,.2f}".format(valor).replace(",", "v").replace(".", ",").replace("v", ".")
    except (ValueError, TypeError):
        return value

@register.filter
def moeda_eua(value):
    try:
        valor = float(value)
        return "{:,.2f}".format(valor).replace(".", "v").replace(",", ".").replace("v", ",")
    except (ValueError, TypeError):
        return value
    
@register.filter
def preco_tabela(produto, tabela):
    pt = ProdutoTabela.objects.filter(produto=produto, tabela=tabela).first()
    return pt.vl_prod if pt else None