from django.db import models
from filiais.models import Filial
from fornecedores.models import Fornecedor
from produtos.models import Produto

class Entrada(models.Model):
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    vinc_fil = models.ForeignKey('filiais.Filial', on_delete=models.CASCADE)
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.CASCADE)
    numeracao = models.CharField(max_length=25)
    dt_emi = models.DateField(null=True, blank=True)
    dt_ent = models.DateField(null=True, blank=True)
    tp_frete = models.CharField(
        max_length=3,
        choices=[('CIF', 'CIF'), ('FOB', 'FOB')],
        default='CIF'
    )
    tipo = models.CharField(
        max_length=12,
        choices=[('Pedido', 'Pedido'), ('Nota Fiscal', 'Nota Fiscal')]
    )
    situacao = models.CharField(
        max_length=10,
        choices=[('Pendente', 'Pendente'), ('Efetivada', 'Efetivada'), ('Cancelada', 'Cancelada')],
        default='Pendente'
    )
    modelo = models.CharField(max_length=2, blank=True, null=True)
    serie = models.CharField(max_length=2, blank=True, null=True)
    nat_op = models.CharField(max_length=255, blank=True, null=True)
    chave_acesso = models.CharField(max_length=44, blank=True, null=True)
    obs = models.TextField(default="", blank=True)
    frete = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    motivo = models.CharField(max_length=100, blank=True, null=True)

    def atualizar_total(self):
        total = sum(item.subtotal for item in self.itens.all())
        self.total = total + self.frete
        return total

    def save(self, *args, **kwargs):
        # primeiro salva para garantir que a entrada exista (id válido)
        super().save(*args, **kwargs)
        # depois recalcula o total
        self.atualizar_total()
        super().save(update_fields=["total"])

    def __str__(self):
        return f"{self.vinc_fil.fantasia} - {self.id}"

    class Meta:
        verbose_name_plural = "Entradas de NF/Pedidos"
        permissions = [
            ("efetivar_entrada", "Pode efetivar entrada de notas/pedidos"),
            ("cancelar_entrada", "Pode cancelar entrada de notas/pedidos"),
        ]


class EntradaProduto(models.Model):
    entrada = models.ForeignKey(Entrada, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name="produtos_vinculados")
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    desconto = models.DecimalField(max_digits=10, decimal_places=2)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["entrada", "produto"], name="uniq_conf_relacao")
        ]

    @property
    def subtotal(self):
        return (self.preco_unitario * self.quantidade) - self.desconto

    def __str__(self):
        return f"{self.produto.id} - {self.produto.desc_prod} ({self.quantidade} x {self.preco_unitario})"