from django.db import models
from filiais.models import Filial
from unidecode import unidecode
from grupos.models import Grupo
from marcas.models import Marca
from unidades.models import Unidade
from tabelas_preco.models import TabelaPreco
from django.core.exceptions import ValidationError
from regras_produto.models import RegraProduto

class Produto(models.Model):
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    grupo = models.ForeignKey(Grupo, on_delete=models.SET_NULL, null=True)
    marca = models.ForeignKey(Marca, on_delete=models.SET_NULL, null=True)
    unidProd = models.ForeignKey(Unidade, on_delete=models.SET_NULL, null=True)
    situacao = models.CharField(
        verbose_name="Situação",
        max_length=50,
        choices=[
            ('Ativo', 'Ativo'),
            ('Inativo', 'Inativo'),
        ],
        default="Ativo"
    )
    tp_prod = models.CharField(
        verbose_name="Tipo do Produto",
        max_length=50,
        choices=[
            ('Principal', 'Principal'),
            ('Adicional', 'Adicional'),
        ]
    )
    lista_orc = models.BooleanField(default=False, verbose_name="Exibir na Lista (Orçamentos)")
    desc_prod = models.CharField(max_length=50)
    desc_normalizado = models.CharField(max_length=255, blank=True, null=True)

    vl_compra = models.CharField(max_length=50, default='0.00')
    estoque_prod = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    regra = models.ForeignKey(
        RegraProduto,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    def save(self, *args, **kwargs):
        self.desc_prod = self.desc_prod.upper()
        self.desc_normalizado = unidecode(self.desc_prod).lower()
        super(Produto, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.desc_prod}"

    class Meta:
        verbose_name_plural = "Produtos"
        permissions = [
            ("clonar_produto", "Pode clonar produtos"),
        ]

class ProdutoTabela(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    tabela = models.ForeignKey(TabelaPreco, on_delete=models.CASCADE)
    vl_prod = models.DecimalField(max_digits=10, decimal_places=2)
    margem = models.DecimalField(max_digits=10, decimal_places=2)
    class Meta:
        verbose_name = "Tabela de preço por produto"
        verbose_name_plural = "Tabelas de preço por produto"
        unique_together = ('produto', 'tabela')

    def __str__(self):
        return f"{self.produto.desc_prod} — {self.tabela.descricao} (R$ {self.vl_prod}) Margem: {self.margem}%"

class CodigoProduto(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='codigos')
    codigo = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"{self.codigo} ({self.produto.desc_prod})"

    def clean(self):
        if CodigoProduto.objects.exclude(pk=self.pk).filter(codigo=self.codigo).exists():
            raise ValidationError({'codigo': 'Este código já está vinculado a outro produto.'})
