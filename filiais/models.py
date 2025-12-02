from django.db import models
import unicodedata
from django.contrib.auth.models import User
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
import re
from datetime import datetime
from bancos.models import Banco
from empresas.models import Empresa
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado
from django.contrib.auth.models import AbstractUser

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

def data_hoje_formatada():
    return datetime.now().strftime('%d/%m/%Y')

class Filial(models.Model):
    situacao = models.CharField(
        max_length=10,
        verbose_name="Situação",
        choices=[
            ('Ativa', 'Ativa'),
            ('Inativa', 'Inativa')
        ]
    )
    layout_contrato = models.CharField(
        max_length=10,
        verbose_name="Layout Contrato",
        choices=[
            ('Layout 1', 'Layout 1'),
            ('Layout 2', 'Layout 2')
        ],
        default="Layout 1"
    )
    tp_chave = models.CharField(
        max_length=20,
        verbose_name="Tipo de Chave Pix",
        choices=[
            ('CPF', 'CPF'),
            ('CNPJ', 'CNPJ'),
            ('E-mail', 'E-mail'),
            ('Telefone', 'Telefone'),
            ('Chave Aleatória', 'Chave Aleatória')
        ]
    )
    chave_pix = models.CharField(
        max_length=100,
        verbose_name="Chave Pix"
    )
    banco_fil = models.ForeignKey('bancos.Banco', on_delete=models.CASCADE, null=True, blank=True)

    beneficiario = models.CharField(max_length=255, verbose_name='Nome Beneficiário')

    info_comp = models.TextField(default="Obrigado pela preferência!", blank=True)

    info_orcamento = models.TextField(default="*Caro cliente, caso você encontre um orçamento com valor inferior, podemos analisar o orçamento concorrente para fecharmos negócio.", blank=True)

    cnpj = models.CharField(max_length=20, verbose_name='CNPJ')
    ie = models.CharField(max_length=20, verbose_name='Inscrição Estadual')
    razao_social = models.CharField(max_length=100, verbose_name='Razão Social')
    fantasia = models.CharField(max_length=100, verbose_name='Fantasia')
    endereco = models.CharField(max_length=100, verbose_name='Endereço')
    cep = models.CharField(max_length=10, verbose_name='CEP')
    numero = models.CharField(max_length=10, verbose_name='Nº')
    bairro_fil = models.ForeignKey('bairros.Bairro', on_delete=models.SET_NULL, null=True)
    complem = models.CharField(max_length=20, verbose_name='Complemento', blank=True)
    cidade_fil = models.ForeignKey('cidades.Cidade', on_delete=models.SET_NULL, null=True)
    uf = models.ForeignKey('estados.Estado', on_delete=models.SET_NULL, null=True)
    tel = models.CharField(max_length=15, verbose_name='Fone')
    email = models.EmailField(max_length=40, verbose_name='E-mail')
    fantasia_normalizado = models.CharField(max_length=255, editable=False)
    logo = models.FileField(upload_to='logo/', null=True, blank=True, default='default_logo.png')
    vinc_emp = models.ForeignKey(Empresa, on_delete=models.CASCADE)

    dt_criacao = models.CharField(
        max_length=30,
        verbose_name='Data de Registro',
        default=data_hoje_formatada
    )
    dt_inativacao = models.CharField(max_length=30, verbose_name='Data de Inativação', blank=True, null=True)

    principal = models.BooleanField(default=False, verbose_name='Filial Principal')
    vinculada_a = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='filiais_secundarias', verbose_name='Filial Vinculada à')
    def save(self, *args, **kwargs):
        self.cnpj = self.cnpj.upper()
        self.ie = self.ie.upper()
        self.razao_social = self.razao_social.upper()
        self.fantasia = self.fantasia.upper()
        self.beneficiario = self.beneficiario.upper()
        self.endereco = self.endereco.upper()
        self.cep = self.cep.upper()
        self.numero = self.numero.upper()
        self.complem = self.complem.upper()
        self.tel = self.tel.upper()
        self.email = self.email.lower()
        self.fantasia_normalizado = remove_accents(self.fantasia).lower()
        self.fantasia = self.fantasia_normalizado
        if self.logo and self.logo.name != 'media/default_logo.png':  # Ignorar o redimensionamento da logo padrão
            # Abrir a imagem da logo
            img = Image.open(self.logo)

            # Definir o tamanho desejado para a logo
            max_size = (300, 300)  # Redimensionar para 300x300 (ajustável)

            # Redimensionar a imagem mantendo a proporção
            img.thumbnail(max_size)

            # Salvar a nova imagem redimensionada em um arquivo temporário
            img_io = BytesIO()
            img.save(img_io, format='PNG')  # Salve no formato desejado, aqui 'PNG'
            img_content = ContentFile(img_io.getvalue(), name=f'{self.id}.png')
        super(Filial, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.fantasia}"

    class Meta:
        verbose_name_plural = "Filiais"

class Usuario(AbstractUser):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="usuarios", null=True, blank=True)
    filial_user = models.ForeignKey(Filial, on_delete=models.SET_NULL, null=True, blank=True, related_name="usuarios")
    codigo_local = models.PositiveIntegerField(blank=True, null=True)
    gerar_senha_lib = models.BooleanField(default=False, verbose_name='Gerar Senha de Liberação')
    senha_liberacao = models.CharField(max_length=20, blank=True, null=True, verbose_name='Senha de Liberação')
    is_master = models.BooleanField(default=False)

    class Meta:
        unique_together = ('username', 'empresa')

    def save(self, *args, **kwargs):
        if self.empresa and not self.codigo_local:
            ultimo = Usuario.objects.filter(empresa=self.empresa).aggregate(
                models.Max('codigo_local')
            )['codigo_local__max'] or 0
            self.codigo_local = ultimo + 1
        super().save(*args, **kwargs)

    def __str__(self):
        if self.empresa:
            if self.filial_user:
                return f"{self.username} - Emp: {self.empresa.fantasia}/Filial P.: {self.filial_user.fantasia}"
            return f"{self.username} - Emp: {self.empresa.fantasia}"
        return f"{self.username} (GLOBAL)"
