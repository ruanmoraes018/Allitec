from django.db import models
from empresas.models import Empresa
from datetime import date
from contratos.models import Contrato


class Mensalidade(models.Model):
    SITUACAO_CHOICES = [
        ('Aberta', 'Aberta'),
        ('Baixada', 'Baixada')
    ]

    TIPO_PAGAMENTO_CHOICES = [
        ('Boleto', 'Boleto'),
        ('Pix', 'Pix')
    ]

    situacao = models.CharField(
        max_length=10,
        choices=SITUACAO_CHOICES,
        default='Aberta'
    )
    num_mens = models.CharField(max_length=10, verbose_name="Nr. Mensalidade", null=True, blank=True)
    dt_venc = models.DateField(null=True, blank=True)
    dt_pag = models.DateField(null=True, blank=True)

    tp_mens = models.CharField(
        max_length=10,
        choices=TIPO_PAGAMENTO_CHOICES,
        default='Pix'
    )
    qtd_mens = models.IntegerField()
    vl_mens = models.DecimalField(max_digits=10, decimal_places=2)
    obs = models.TextField(blank=True, null=True)

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def atrasada(self):
        return (
            self.situacao == 'Aberta' and
            self.dt_venc is not None and
            self.dt_venc < date.today()
        )

    def __str__(self):
        return f'{self.empresa} - Venc.: {self.dt_venc} - {self.situacao}'

    class Meta:
        verbose_name_plural = "Mensalidades"
        ordering = ['-dt_venc']
