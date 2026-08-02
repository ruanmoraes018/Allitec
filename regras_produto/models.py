from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils.text import slugify
import json

class GrupoRegraProduto(models.Model):
    cod_local = models.PositiveIntegerField(blank=True, null=True)
    vinc_emp = models.ForeignKey("empresas.Empresa", on_delete=models.CASCADE, related_name="grupos_regras_produto")
    codigo = models.CharField(max_length=50)
    descricao = models.CharField(max_length=100)
    ordem = models.PositiveIntegerField(default=0)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["ordem", "codigo"]
        constraints = [
            models.UniqueConstraint(fields=["vinc_emp", "codigo"], name="unique_grupo_regra_empresa")
        ]

    def __str__(self):
        return self.descricao.upper()
    
    def save(self,*args,**kwargs):
        if self.vinc_emp and not self.cod_local:
            with transaction.atomic():
                ult = (GrupoRegraProduto.objects.select_for_update().filter(vinc_emp=self.vinc_emp).aggregate(models.Max('cod_local'))['cod_local__max'] or 0) 
                self.cod_local = ult + 1

                self.codigo = self.codigo.strip().upper()
                self.descricao = self.descricao.strip().upper()
        super().save(*args,**kwargs)

class RegraProduto(models.Model):
    class Tipo(models.TextChoices):
        SELECAO = "SELECAO", "Selecionar Produto"
        CALCULO = "CALCULO", "Calcular Quantidade"
        ADICIONAL = "ADICIONAL", "Adicionar Item"
        VALIDACAO = "VALIDACAO", "Validação"
    cod_local = models.PositiveIntegerField(blank=True, null=True)
    vinc_emp = models.ForeignKey("empresas.Empresa", on_delete=models.CASCADE, related_name="regras_produto")
    grupo = models.ForeignKey(GrupoRegraProduto, on_delete=models.PROTECT, related_name="regras", null=True, blank=True)
    codigo = models.CharField(max_length=50)
    descricao = models.CharField(max_length=150)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    categoria = models.CharField(
        max_length=30,
        choices=[("lamina","Lâmina"), ("motor","Motor"), ("eixo","Eixo"), ("mola","Mola"), ("pintura","Pintura"),("testeira",  "Testeira"), ("acessorio","Acessório"), ("outro","Outro"),],
        default="outro"
    )
    ordem = models.PositiveIntegerField(default=0)
    formula = models.JSONField(blank=True, null=True, help_text="Somente fórmulas e parâmetros extras")
    ativo = models.BooleanField(default=True)
    criado_em=models.DateTimeField(auto_now_add=True)
    alterado_em=models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["grupo", "ordem", "codigo"]
        indexes = [models.Index(fields=["vinc_emp"]), models.Index(fields=["grupo"]),]
        constraints = [
            models.UniqueConstraint(fields=['codigo', 'vinc_emp'], name='unique_codigo_regra_por_empresa'),
            models.UniqueConstraint(fields=['cod_local', 'vinc_emp'], name='unique_cod_local_regra_empresa')
        ]
    def save(self,*args,**kwargs):
        self.codigo=self.codigo.strip().upper()
        self.descricao=self.descricao.strip().upper()
        if self.vinc_emp and not self.cod_local:
            with transaction.atomic():
                ult = (RegraProduto.objects.select_for_update().filter(vinc_emp=self.vinc_emp).aggregate(models.Max('cod_local'))['cod_local__max'] or 0) 
                self.cod_local = ult + 1
        super().save(*args,**kwargs)

class RegraProdutoItem(models.Model):
    regra=models.ForeignKey(RegraProduto, related_name="itens", on_delete=models.CASCADE)
    produto=models.ForeignKey("produtos.Produto", on_delete=models.PROTECT)
    formula_qtd=models.CharField(max_length=100, default="1")
    descricao=models.CharField(max_length=150, blank=True)
    prioridade=models.PositiveIntegerField(default=0)

    class Meta:
        ordering=["prioridade"]

    def __str__(self):
        return str(self.produto)

class CondicaoRegraProduto(models.Model):
    class Operador(models.TextChoices):
        IGUAL="=","Igual"
        MAIOR=">", "Maior"
        MENOR="<","Menor"
        MAIOR_IGUAL=">=","Maior ou igual"
        MENOR_IGUAL="<=","Menor ou igual"
        IN="IN","Está entre"
    item = models.ForeignKey(RegraProdutoItem, related_name="condicoes", on_delete=models.CASCADE, null=True, blank=True)
    regra = models.ForeignKey(RegraProduto, related_name="condicoes", on_delete=models.CASCADE, null=True, blank=True)
    campo=models.CharField(max_length=50)
    operador=models.CharField(max_length=5, choices=Operador.choices)
    valor=models.JSONField()
    ordem=models.PositiveIntegerField(default=0)

    class Meta:
        ordering=["ordem"]

    def __str__(self):
        return f"{self.campo} {self.operador} {self.valor}"
    
class BloqueioRegraProduto(models.Model):
    regra=models.ForeignKey(RegraProduto, related_name="bloqueios", on_delete=models.CASCADE)
    mensagem=models.TextField()
    ativo=models.BooleanField(default=True)

    def __str__(self):
        return self.mensagem[:50]

class ResultadoRegraPorta(models.Model):
    porta=models.ForeignKey("orcamentos.PortaOrcamento", related_name="resultados_regras", on_delete=models.CASCADE)
    regra=models.ForeignKey(RegraProduto, on_delete=models.PROTECT)
    produto=models.ForeignKey("produtos.Produto",  on_delete=models.PROTECT)
    quantidade=models.DecimalField(max_digits=10, decimal_places=2, default=1)
    contexto=models.JSONField(default=dict)
    criado_em=models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes=[
            models.Index(fields=["porta", "regra"])
        ]