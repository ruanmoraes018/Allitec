from django.db import models
from django.core.exceptions import ValidationError
from core.pagamentos.credenciais import CREDENCIAIS_GATEWAY
import json

class FormaPgto(models.Model):
    descricao = models.CharField(max_length=100, unique=True)

    situacao = models.CharField(
        max_length=7,
        choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')]
    )

    troco = models.CharField(
        max_length=3,
        choices=[('Sim', 'Sim'), ('Não', 'Não')],
        default='Não'
    )

    tipo = models.CharField(
        max_length=8,
        choices=[('A vista', 'A vista'), ('A prazo', 'A prazo')]
    )

    gera_parcelas = models.BooleanField(default=False)

    vinc_emp = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    # 🔥 Gateway dinâmico
    gateway = models.CharField(
        max_length=20,
        choices=[
            ('nenhum', 'Nenhum'),
            ('mercadopago', 'Mercado Pago'),
            ('pagseguro', 'PagSeguro'),
            ('stripe', 'Stripe'),
            ('pix_direto', 'Pix Direto'),
        ],
        default='nenhum'
    )

    # 🔥 Credenciais flexíveis
    credenciais = models.JSONField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.descricao = self.descricao.strip().upper()
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        if self.gateway == "nenhum":
            return

        cred = self.credenciais

        # 🔥 GARANTE QUE É DICT
        if isinstance(cred, str):
            try:
                cred = json.loads(cred)
            except:
                raise ValidationError("Credenciais inválidas")

        if not cred:
            raise ValidationError("Credenciais obrigatórias para este gateway")

        obrigatorios = CREDENCIAIS_GATEWAY.get(self.gateway, [])

        faltando = [
            campo for campo in obrigatorios
            if campo not in cred or not cred.get(campo)
        ]

        if faltando:
            raise ValidationError(
                f"Campos obrigatórios faltando: {', '.join(faltando)}"
            )

        # 🔥 salva já convertido
        self.credenciais = cred

    def get_credencial(self, chave):
        return (self.credenciais or {}).get(chave)

    def __str__(self):
        return self.descricao

    class Meta:
        verbose_name_plural = "Formas de Pagamento"