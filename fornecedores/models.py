from django.db import models
import unicodedata
from filiais.models import Filial
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado
from django.db import transaction

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

class Fornecedor(models.Model):
    codigo = models.PositiveIntegerField(blank=True, null=True)
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    situacao = models.CharField(max_length=10, verbose_name="Situação", choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')])
    pessoa = models.CharField(max_length=10, verbose_name="Pessoa", choices=[('Física', 'Física'), ('Jurídica', 'Jurídica')])
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
    complem = models.CharField(max_length=30, blank=True, null=True, default="")
    tel = models.CharField(max_length=30)
    email = models.EmailField(max_length=40, blank=True, null=True)
    dt_reg = models.DateField(verbose_name="Data de Registro", null=True, blank=True, db_index=True)
    def save(self, *args, **kwargs):
        if self.vinc_emp and not self.codigo:
            with transaction.atomic():
                ult = (Fornecedor.objects.select_for_update().filter(vinc_emp=self.vinc_emp).aggregate(models.Max('codigo'))['codigo__max'] or 0)
                self.codigo = ult + 1
                self.razao_social = self.razao_social.strip().upper()
                self.fantasia = self.fantasia.strip().upper()
                self.endereco = self.endereco.strip().upper()
                self.complem = self.complem.strip().upper()
                self.email = self.email.strip().lower()
                super().save(*args, **kwargs)
        else:
            self.razao_social = self.razao_social.strip().upper()
            self.fantasia = self.fantasia.strip().upper()
            self.endereco = self.endereco.strip().upper()
            self.complem = self.complem.strip().upper()
            self.email = self.email.strip().lower()
            super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.fantasia}"

    class Meta:
        verbose_name_plural = "Fornecedores"
        constraints = [
            models.UniqueConstraint(fields=['cpf_cnpj', 'vinc_emp'], name='unique_cpf_cnpj_fornecedor_por_empresa'),
            models.UniqueConstraint(fields=['codigo', 'vinc_emp'], name='unique_codigo_fornecedor_empresa')
        ]