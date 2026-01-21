from django.db import models

class RegraProduto(models.Model):
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    codigo = models.CharField(
        max_length=50,
        help_text="Identificador interno da regra (ex: MOTOR, LAMINA, PINTURA)"
    )

    descricao = models.CharField(
        max_length=100,
        help_text="Descrição legível da regra"
    )

    tipo = models.CharField(
        max_length=20,
        choices=[
            ('QTD', 'Cálculo de Quantidade'),
            ('SELECAO', 'Seleção Automática'),
        ]
    )

    expressao = models.TextField(
        help_text="Fórmula ou regra (ex: m2, alt_c * 4, JSON para seleção)"
    )

    ativo = models.BooleanField(default=True)
    class Meta:
        unique_together = ('vinc_emp', 'codigo')
    def __str__(self):
        return f"{self.codigo} - {self.descricao}"
    

