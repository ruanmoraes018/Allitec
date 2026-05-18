from django.db import models
import unicodedata
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado
from datetime import datetime
from django.db import transaction

def data_hoje_formatada():
    return datetime.now().strftime('%d/%m/%Y')

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

class Tecnico(models.Model):
    codigo = models.PositiveIntegerField(blank=True, null=True)
    vinc_emp = models.ForeignKey("empresas.Empresa", on_delete=models.CASCADE)
    situacao = models.CharField(max_length=10, verbose_name="Situação", choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')])
    nome = models.CharField(max_length=100)
    endereco = models.CharField(max_length=100)
    cep = models.CharField(max_length=10)
    numero = models.CharField(max_length=10)
    bairro = models.ForeignKey(Bairro, on_delete=models.SET_NULL, null=True)
    cidade = models.ForeignKey(Cidade, on_delete=models.SET_NULL, null=True)
    uf = models.ForeignKey(Estado, on_delete=models.SET_NULL, null=True)
    tel = models.CharField(max_length=30)
    email = models.EmailField(max_length=40)
    dt_reg = models.DateField(verbose_name="Data de Registro", null=True, blank=True, db_index=True)
    def save(self, *args, **kwargs):
        if self.vinc_emp and not self.codigo:
            with transaction.atomic():
                ult = (Tecnico.objects.select_for_update().filter(vinc_emp=self.vinc_emp).aggregate(models.Max('codigo'))['codigo__max'] or 0)
                self.codigo = ult + 1
                self.nome = self.nome.strip().upper()
                self.endereco = self.endereco.strip().upper()
                self.email = self.email.strip().lower()
                super().save(*args, **kwargs)
        else:
            self.nome = self.nome.strip().upper()
            self.endereco = self.endereco.strip().upper()
            self.email = self.email.strip().lower()
            super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.nome}"
    class Meta:
        verbose_name_plural = "Técnicos"
        constraints = [models.UniqueConstraint(fields=['codigo', 'vinc_emp'], name='unique_codigo_tecnico_empresa')]