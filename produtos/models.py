from django.db import models
from unidecode import unidecode
from grupos.models import Grupo
from marcas.models import Marca
from unidades.models import Unidade
from tabelas_preco.models import TabelaPreco
from django.core.exceptions import ValidationError

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
        ],
        blank=True,
        null=True
    )
    lista_orc = models.BooleanField(default=False, verbose_name="Exibir na Lista (Orçamentos)")
    desc_prod = models.CharField(max_length=50)
    desc_normalizado = models.CharField(max_length=255, blank=True, null=True)

    vl_compra = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estoque_prod = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    especifico = models.CharField(verbose_name='Produto Específico', null=True, blank=True, max_length=50, choices=[('', ''), ('Portinhola', 'Portinhola'), ('Alçapão', 'Alçapão'), ('Coluna Removível', 'Coluna Removível'), ('Serviço/Transporte', 'Serviço/Transporte'),], default='')

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

    def clean(self):
        if self.produto and self.tabela:
            if self.produto.vinc_emp != self.tabela.vinc_emp:
                raise ValidationError('O produto e a tabela de preço devem pertencer à mesma empresa.')
    def get_preco_tabela(self, tabela):
        pt = ProdutoTabela.objects.filter(produto=self, tabela=tabela).first()
        return pt.vl_prod if pt else None

class ProdutoFornecedor(models.Model):
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    fornecedor = models.ForeignKey(
        'fornecedores.Fornecedor',
        on_delete=models.CASCADE,
        related_name='produtos_fornecedor'
    )

    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name='fornecedores_vinculados'
    )
    codigo_fornecedor = models.CharField(max_length=60, blank=True, default='')
    descricao_fornecedor = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.fornecedor} -> {self.produto} [{self.codigo_fornecedor}]"

    def clean(self):
        errors = {}

        if self.produto and self.vinc_emp and self.produto.vinc_emp_id != self.vinc_emp_id:
            errors['produto'] = 'O produto precisa pertencer à mesma empresa do vínculo.'

        if self.fornecedor and self.vinc_emp and self.fornecedor.vinc_emp_id != self.vinc_emp_id:
            errors['fornecedor'] = 'O fornecedor precisa pertencer à mesma empresa do vínculo.'

        if errors:
            raise ValidationError(errors)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['vinc_emp', 'fornecedor', 'codigo_fornecedor'],
                name='unique_codigo_fornecedor_por_empresa'
            )
        ]

class CodigoProduto(models.Model):
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='codigos')
    codigo = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.codigo} ({self.produto.desc_prod})"

    def clean(self):
        if self.produto and self.vinc_emp != self.produto.vinc_emp:
            raise ValidationError({
                'produto': 'O produto precisa pertencer à mesma empresa do código.'
            })

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['vinc_emp', 'codigo'],
                name='unique_codigo_por_empresa'
            )
        ]
