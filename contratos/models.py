from django.db import models
from django.utils import timezone
# Create your models here.
class Contrato(models.Model):
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    SITUACAO_CHOICES = [
        ('Ativo', 'Ativo'),
        ('Baixada', 'Suspenso'),
        ('Cancelado', 'Cancelado'),
        ('Expirado', 'Expirado')
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
    dt_exp = models.DateField(null=True, blank=True)
    qtd_meses = models.IntegerField(default=12)
    valor_mensalidade = models.DecimalField(max_digits=10, decimal_places=2)
    obs = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    @property
    def esta_expirado(self):
        if not self.dt_exp:
            return False
        return timezone.localdate() > self.dt_exp
    def __str__(self):
        return f'Contrato {self.id} - {self.empresa.fantasia}'
    def save(self, *args, **kwargs):
        if self.dt_exp:
            if timezone.localdate() > self.dt_exp:
                self.situacao = 'Expirado'
            else:
                if self.situacao == 'Expirado':
                    self.situacao = 'Ativo'

        super().save(*args, **kwargs)