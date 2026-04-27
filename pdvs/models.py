from django.db import models

# Create your models here.

class CaixaTerminal(models.Model):
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    vinc_fil = models.ForeignKey('filiais.Filial', on_delete=models.CASCADE)
    nome = models.CharField(max_length=50)  # Ex: Caixa 1, Caixa 2
    ativo = models.BooleanField(default=True)
    def __str__(self):
        return self.nome

class Caixa(models.Model):
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    vinc_fil = models.ForeignKey('filiais.Filial', on_delete=models.CASCADE)
    usuario = models.ForeignKey('filiais.Usuario', on_delete=models.SET_NULL, null=True)
    terminal = models.ForeignKey(CaixaTerminal, on_delete=models.PROTECT)
    data_abertura = models.DateTimeField(auto_now_add=True)
    data_fechamento = models.DateTimeField(null=True, blank=True)
    saldo_inicial = models.DecimalField(max_digits=10, decimal_places=2)
    saldo_final = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=10, choices=[('Aberto', 'Aberto'), ('Fechado', 'Fechado')], default="Aberto")  # Aberto / Fechado
    observacao = models.TextField(blank=True)
    diferenca = models.DecimalField(max_digits=10, decimal_places=2, default=0)

class CaixaMovimento(models.Model):
    caixa = models.ForeignKey(Caixa, on_delete=models.CASCADE, related_name="movimentos")
    tipo = models.CharField(max_length=10, choices=[('Entrada', 'Entrada'), ('Saída', 'Saída')])  # Entrada / Saída
    categoria = models.CharField(max_length=20)
    # Ex: VENDA, SANGRIA, SUPRIMENTO, DESPESA
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    descricao = models.CharField(max_length=255, blank=True)
    data_hora = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey('filiais.Usuario', on_delete=models.SET_NULL, null=True)