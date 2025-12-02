from django.db import models
from decimal import Decimal
from filiais.models import Filial
from clientes.models import Cliente
from produtos.models import Produto
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings
from formas_pgto.models import FormaPgto

class Pedido(models.Model):
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    vinc_fil = models.ForeignKey('filiais.Filial', on_delete=models.CASCADE)
    cli = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    vendedor = models.CharField(max_length=100)
    nome_cli = models.CharField(max_length=255, blank=True)

    situacao = models.CharField(
        max_length=10,
        choices=[('Aberto', 'Aberto'), ('Faturado', 'Faturado'), ('Cancelado', 'Cancelado')],
        default='Aberto'
    )

    obs = models.TextField(default="", blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    dt_emi = models.DateTimeField(null=True, blank=True)
    dt_fat = models.DateTimeField(null=True, blank=True)
    motivo = models.CharField(max_length=60, blank=True, null=True)
    def __str__(self):
        return f"{self.id} - {self.cli}"

    def atualizar_total(self):
        total = sum(item.subtotal for item in self.itens.all())
        self.total = total
        return total

    def save(self, *args, **kwargs):
        self.nome_cli = self.cli.fantasia
        # Calcular subtotal antes de salvar
        self.atualizar_total()
        super().save(*args, **kwargs)  # Salva primeiro, garantindo PK
        super().save(update_fields=["total"])


    class Meta:
        verbose_name_plural = "Pedidos"
        permissions = [
            ("clonar_pedido", "Pode clonar pedido"),
            ("faturar_pedido", "Pode faturar pedido"),
            ("cancelar_pedido", "Pode cancelar pedido"),
            ("atribuir_desconto_ped", "Pode atribuir descontos em pedido"),
            ("atribuir_acrescimo_ped", "Pode atribuir acréscimos em pedido"),
        ]


class PedidoProduto(models.Model):
    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE, related_name="itens"
    )
    produto = models.ForeignKey(
        Produto, on_delete=models.CASCADE, related_name="produtos_vinculados_ped"
    )
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    desc_acres = models.DecimalField(verbose_name="Desconto/Acréscimo", max_digits=10, decimal_places=2, default=0)

    @property
    def subtotal(self):
        return (Decimal(str(self.produto.vl_prod)) * self.quantidade) - self.desc_acres

    def __str__(self):
        return f"{self.produto.id} - {self.produto.desc_prod} ({self.quantidade} x {self.produto.vl_prod})"

class PedidoFormaPgto(models.Model):
    pedido = models.ForeignKey("Pedido", on_delete=models.CASCADE, related_name="formas_pgto")
    formas_pgto = models.ForeignKey("formas_pgto.FormaPgto", on_delete=models.PROTECT, related_name="usos_ped")
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["pedido", "formas_pgto"], name="uniq_ped_formapgto")
        ]

    def __str__(self):
        return f"{self.pedido.id} - {self.formas_pgto.descricao}"
