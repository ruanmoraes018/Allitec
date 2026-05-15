
from decimal import Decimal

def parse_decimal(valor):
    if not valor:
        return Decimal('0.00')
    valor = str(valor).strip().replace('R$', '').replace(' ', '')
    tem_virgula = ',' in valor
    tem_ponto = '.' in valor
    if tem_virgula and tem_ponto:
        if valor.rfind(',') > valor.rfind('.'):
            valor = valor.replace('.', '').replace(',', '.')
        else:
            valor = valor.replace(',', '')
    elif tem_virgula:
        valor = valor.replace(',', '.')
    try:
        return Decimal(valor)
    except:
        return Decimal('0.00')
    
def format_decimal_br(valor):
    if valor is None:
        return '0,00'
    valor = Decimal(valor)
    return f'{valor:.2f}'.replace('.', ',')