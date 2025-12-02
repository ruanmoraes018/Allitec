from django.db import models
import unicodedata
from filiais.models import Filial
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

class Fornecedor(models.Model):
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    situacao = models.CharField(
        max_length=10,
        verbose_name="Situação",
        choices=[
            ('Ativo', 'Ativo'),
            ('Inativo', 'Inativo')
        ]
    )
    pessoa = models.CharField(
        max_length=10,
        verbose_name="Pessoa",
        choices=[
            ('Física', 'Física'),
            ('Jurídica', 'Jurídica')
        ]
    )
    cpf_cnpj = models.CharField(max_length=25)
    ie = models.CharField(max_length=20, blank=True, null=True)
    razao_social = models.CharField(max_length=100)
    fantasia = models.CharField(max_length=100)
    endereco = models.CharField(max_length=100)
    cep = models.CharField(max_length=10)
    numero = models.CharField(max_length=10)
    bairro = models.ForeignKey(Bairro, on_delete=models.SET_NULL, null=True)
    cidade = models.ForeignKey(Cidade, on_delete=models.SET_NULL, null=True)
    uf = models.ForeignKey(Estado, on_delete=models.SET_NULL, null=True)
    complem = models.CharField(max_length=30, blank=True, default="")
    tel = models.CharField(max_length=30)
    email = models.EmailField(max_length=40)
    dt_reg = models.DateField(verbose_name="Data de Registro", null=True, blank=True)
    def save(self, *args, **kwargs):
        self.razao_social = self.razao_social.upper()
        self.fantasia = self.fantasia.upper()
        self.endereco = self.endereco.upper()
        self.complem = self.complem.upper()
        self.email = self.email.lower()
        super(Fornecedor, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.fantasia}"

    class Meta:
        verbose_name_plural = "Fornecedores"
