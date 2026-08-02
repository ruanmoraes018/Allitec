import builtins
from django import template
register = template.Library()

@register.filter
def dict_key(d, key):
    try: return d[key]
    except (KeyError, TypeError): return None

@register.filter
def get_item(d, key):
    try: return d[key]
    except (KeyError, TypeError): return None

@register.filter
def abs(value):
    try: return builtins.abs(value)
    except (TypeError, ValueError): return value