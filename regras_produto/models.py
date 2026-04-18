from django.db import models

class RegraProduto(models.Model):
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    produto = models.ForeignKey('produtos.Produto', verbose_name="Produto", null=True, blank=True, on_delete=models.SET_NULL)
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
    tipo_regra = models.CharField(
        max_length=20,
        null=True, blank=True,
        choices=[
            ('', ''),
            ('qtd', 'Quantidade (múltiplos produtos)'),
            ('peso', 'Por Peso (máx)'),
            ('simples', 'Valor Simples'),
        ]
    )
    expressao_json = models.JSONField(blank=True, null=True)
    # expressao = models.TextField(blank=True, null=True,
    #     help_text="Fórmula ou regra (ex: m2 = M², larg = Largura, alt = Altura, larg_c = Largura de Corte, alt_c = Altura de Corte, ft_peso = Fator de Peso, qtd_lam = Quantidade de Lâminas, " +
    #     "eix_mot = Eixo do Motor, alt_c * 4, JSON para seleção com a descrição do produto)"
    # )

    ativo = models.BooleanField(default=True)
    class Meta:
        verbose_name_plural = "Regras de Produto"
        constraints = [
            models.UniqueConstraint(fields=['codigo', 'vinc_emp'], name='unique_codigo_regra_por_empresa')
        ]
    def __str__(self):
        return f"{self.codigo} - {self.descricao}"


