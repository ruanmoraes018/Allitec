from django import template

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