from django.db import models
import unicodedata
from filiais.models import Filial
from datetime import datetime
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado

def data_hoje_formatada():
    return datetime.now().strftime('%d/%m/%Y')

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

class Tecnico(models.Model):
    vinc_emp = models.ForeignKey("empresas.Empresa", on_delete=models.CASCADE)
    situacao = models.CharField(
        max_length=10,
        verbose_name="Situação",
        choices=[
            ('Ativo', 'Ativo'),
            ('Inativo', 'Inativo')
        ]
    )
    nome = models.CharField(max_length=100)
    endereco = models.CharField(max_length=100)
    cep = models.CharField(max_length=10)
    numero = models.CharField(max_length=10)
    bairro = models.ForeignKey(Bairro, on_delete=models.SET_NULL, null=True)
    cidade = models.ForeignKey(Cidade, on_delete=models.SET_NULL, null=True)
    uf = models.ForeignKey(Estado, on_delete=models.SET_NULL, null=True)
    tel = models.CharField(max_length=30)
    email = models.EmailField(max_length=40)
    dt_reg = models.CharField(
        max_length=30,
        verbose_name='Data de Registro',
        default=data_hoje_formatada
    )
    def save(self, *args, **kwargs):
        self.nome = self.nome.upper()
        self.endereco = self.endereco.upper()
        self.email = self.email.lower()
        super(Tecnico, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome}"

    class Meta:
        verbose_name_plural = "Técnicos"
