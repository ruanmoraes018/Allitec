from num2words import num2words
from decimal import Decimal

def vl_extenso(valor):
    valor = Decimal(valor)
    inteiro = int(valor)
    centavos = int(round((valor - inteiro) * 100))
    texto = num2words(inteiro, lang='pt_BR')
    if inteiro == 1: texto += " real"
    else: texto += " reais"
    if centavos > 0:
        texto += " e "
        texto += num2words(centavos, lang='pt_BR')
        texto += " centavo" if centavos == 1 else " centavos"
    return texto.capitalize()