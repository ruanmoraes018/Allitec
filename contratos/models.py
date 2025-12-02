from django.db import models
from empresas.models import Empresa
# Create your models here.
class Contrato(models.Model):
    # empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    SITUACAO_CHOICES = [
        ('Ativo', 'Ativo'),
        ('Baixada', 'Suspenso'),
        ('Cancelado', 'Cancelado')
    ]
    situacao = models.CharField(
        max_length=10,
        choices=SITUACAO_CHOICES,
        default='Ativo'
    )
    STATUS_CHOICES = [
        ('Pendente', 'Pendente'),
        ('Aprovado', 'Aprovado')
    ]
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='Pendente'
    )
    dt_inicio = models.DateField()
    qtd_parcelas = models.IntegerField()
    valor_mensalidade = models.DecimalField(max_digits=10, decimal_places=2)
    obs = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Contrato {self.id} - {self.empresa.fantasia}'