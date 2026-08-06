from django.db import models
import unicodedata
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from datetime import datetime
from empresas.models import Empresa
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import transaction
from django.conf import settings
from django.core.files.storage import default_storage

def caminho_logo_filial(instance, filename):
    ext = filename.split('.')[-1]
    return f"logo/logo_{instance.pk}.{ext}"

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

def data_hoje_formatada():
    return datetime.now().strftime('%d/%m/%Y')

class Filial(models.Model):
    codigo = models.PositiveIntegerField(blank=True, null=True)
    situacao = models.CharField(max_length=10, verbose_name="Situação", choices=[('Ativa', 'Ativa'), ('Inativa', 'Inativa')])
    cnpj = models.CharField(max_length=20, verbose_name='CNPJ')
    ie = models.CharField(max_length=20, verbose_name='Inscrição Estadual', blank=True, null=True)
    razao_social = models.CharField(max_length=100, verbose_name='Razão Social')
    fantasia = models.CharField(max_length=100, verbose_name='Fantasia')
    endereco = models.CharField(max_length=100, verbose_name='Endereço')
    cep = models.CharField(max_length=10, verbose_name='CEP')
    numero = models.CharField(max_length=10, verbose_name='Nº')
    tb_preco = models.ForeignKey('tabelas_preco.TabelaPreco', on_delete=models.SET_NULL, null=True)
    vendedor = models.ForeignKey('vendedores.Vendedor', on_delete=models.SET_NULL, null=True, blank=True)
    cli = models.ForeignKey('clientes.Cliente', on_delete=models.SET_NULL, null=True)
    tec = models.ForeignKey('tecnicos.Tecnico', on_delete=models.SET_NULL, null=True, blank=True)
    tp_conta = models.ForeignKey('tipo_cobranca.TipoCobranca', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Tipo de Conta")
    bairro_fil = models.ForeignKey('bairros.Bairro', on_delete=models.SET_NULL, null=True, blank=True)
    complem = models.CharField(max_length=20, verbose_name='Complemento', blank=True)
    cidade_fil = models.ForeignKey('cidades.Cidade', on_delete=models.SET_NULL, null=True)
    uf = models.ForeignKey('estados.Estado', on_delete=models.SET_NULL, null=True)
    tel = models.CharField(max_length=15, verbose_name='Fone')
    fantasia_normalizado = models.CharField(max_length=255, editable=False)
    logo = models.FileField(upload_to=caminho_logo_filial, null=True, blank=True, default='default_logo.png')
    vinc_emp = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    dt_criacao = models.DateField(verbose_name="Data de Registro", null=True, blank=True, db_index=True)
    dt_inativacao = models.DateField(verbose_name="Data de Inativação", null=True, blank=True, db_index=True)
    principal = models.BooleanField(default=False, verbose_name='Filial Principal')
    vinculada_a = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='filiais_secundarias', verbose_name='Filial Vinculada à')
    agrupa_itens = models.BooleanField(default=True, verbose_name="Agrupar itens no pedido")

    def garantir_configuracoes(self):
        FilialFinanceiro.objects.get_or_create(filial=self)
        FilialFiscal.objects.get_or_create(filial=self)
        FilialOrcamento.objects.get_or_create(filial=self)
        FilialContato.objects.get_or_create(filial=self)
        FilialEstoque.objects.get_or_create(filial=self)
        FilialImpressao.objects.get_or_create(filial=self)
        FilialObservacao.objects.get_or_create(filial=self)

    def save(self, *args, **kwargs):
        if self.pk:
            antiga = Filial.objects.get(pk=self.pk)
            if antiga.logo and self.logo != antiga.logo:
                if default_storage.exists(antiga.logo.name):
                    default_storage.delete(antiga.logo.name)

        super().save(*args, **kwargs)
        if self.vinc_emp and not self.codigo:
            with transaction.atomic():
                ult = (Filial.objects.select_for_update().filter(vinc_emp=self.vinc_emp).aggregate(models.Max('codigo'))['codigo__max'] or 0)
                self.codigo = ult + 1
                self.razao_social = self.razao_social.strip().upper()
                self.endereco = self.endereco.strip().upper()
                self.complem = self.complem.strip().upper()
                super().save(*args, **kwargs)
        else:
            self.razao_social = self.razao_social.strip().upper()
            self.endereco = self.endereco.strip().upper()
            self.complem = self.complem.strip().upper()
            super().save(*args, **kwargs)

    def clean(self):
        if self.principal:
            qs = Filial.objects.filter(vinc_emp=self.vinc_emp, principal=True)
            if self.pk: qs = qs.exclude(pk=self.pk)
            if qs.exists(): raise ValidationError("Já existe uma filial principal para esta empresa.")
    def __str__(self):
        return f"{self.fantasia}"

    class Meta:
        verbose_name_plural = "Filiais"
        constraints = [models.UniqueConstraint(fields=['codigo', 'vinc_emp'], name='unique_codigo_filial_empresa')]

class FilialFinanceiro(models.Model):
    filial = models.OneToOneField('filiais.Filial', on_delete=models.CASCADE, related_name='financeiro')
    tp_chave = models.CharField(max_length=20, verbose_name="Tipo de Chave Pix", choices=[('CPF', 'CPF'), ('CNPJ', 'CNPJ'), ('E-mail', 'E-mail'), ('Telefone', 'Telefone'), ('Chave Aleatória', 'Chave Aleatória')])
    chave_pix = models.CharField(max_length=100, verbose_name="Chave Pix", null=True, blank=True)
    banco_fil = models.ForeignKey('bancos.Banco', on_delete=models.SET_NULL, null=True, blank=True)
    beneficiario = models.CharField(max_length=255, verbose_name='Nome Beneficiário', null=True, blank=True)
    max_parcelas = models.PositiveIntegerField(default=1)
    max_dias_intervalo = models.PositiveIntegerField(default=30)
    tp_calc_juros = models.CharField(max_length=15, verbose_name="Tp. Cálculo Juros", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], default="Percentual")
    tp_calc_multa = models.CharField(max_length=15, verbose_name="Tp. Cálculo Multa", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], default="Percentual")
    ft_multa = models.DecimalField(verbose_name="Fator Multa", max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    ft_juros = models.DecimalField(verbose_name="Fator Juros",max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    desconto_maximo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    acrescimo_maximo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    limite_credito_padrao = models.DecimalField(max_digits=12, decimal_places=2, default=0)

class FilialFiscal(models.Model):
    filial = models.OneToOneField('filiais.Filial', on_delete=models.CASCADE, related_name='fiscal')
    crt = models.CharField(max_length=5, choices=[("1", "Simples Nacional"), ("2", "Simples Nacional Excesso"), ("3", "Regime Normal")], default="1", verbose_name="CRT")
    im = models.CharField(max_length=30, blank=True, null=True, verbose_name="Inscrição Municipal")
    suframa = models.CharField(max_length=30, blank=True, null=True)
    certificado = models.FileField(upload_to="certificados/", blank=True, null=True)
    senha_certificado = models.CharField(max_length=150, blank=True, null=True)
    serie_nfe = models.PositiveIntegerField(default=1)
    serie_nfce = models.PositiveIntegerField(default=1)
    ultimo_numero_nfe = models.PositiveIntegerField(default=0)
    ultimo_numero_nfce = models.PositiveIntegerField(default=0)
    ambiente_fiscal = models.CharField(max_length=15, choices=[("Homologação", "Homologação"), ("Produção", "Produção")], default="Homologação")
    cnae_principal = models.CharField(max_length=20, blank=True, null=True)
    csc = models.CharField(max_length=30, blank=True, null=True, verbose_name="CSC")
    cod_csc = models.CharField(max_length=30, blank=True, null=True, verbose_name="ID CSC")
    validade_certificado = models.DateField(null=True, blank=True)
    titular_certificado = models.CharField(max_length=255, blank=True)
    cnpj_certificado = models.CharField(max_length=18, blank=True)
    numero_serie = models.CharField(max_length=100, blank=True)
    autoridade_certificadora = models.CharField(max_length=255, blank=True)

class FilialOrcamento(models.Model):
    filial = models.OneToOneField('filiais.Filial', on_delete=models.CASCADE, related_name='orcamento_porta')
    layout_contrato = models.CharField(max_length=10, verbose_name="Layout Contrato", choices=[('Layout 1', 'Layout 1'), ('Layout 2', 'Layout 2')], default="Layout 1")
    layout_prod = models.CharField(max_length=10, verbose_name="L. PDF Produção", choices=[('1', 'Layout 1'), ('2', 'Layout 2')], default="1")
    imp_recibo_orc = models.CharField(max_length=20, verbose_name="Questionar Imp. de Recibo", choices=[('Sim','Sim'), ('Não', 'Não'), ('Auto', 'Auto')], default='Sim')
    info_comp = models.TextField(default="Obrigado pela preferência!", blank=True, null=True)
    info_local = models.TextField(default="Atendemos em todo estado do Pará!", blank=True, null=True)
    info_orcamento = models.TextField(default="*Caro cliente, caso você encontre um orçamento com valor inferior, podemos analisar o orçamento concorrente para fecharmos negócio.", blank=True, null=True)
    mt_qt_lam = models.CharField(verbose_name="Multip. Qtde. Lâminas", max_length=100, default="(alt_corte + rolo) / 0.075", null=True, blank=True)
    multi_m2 = models.DecimalField(verbose_name="Multiplicador M²", max_digits=10, decimal_places=2, default=1, null=True, blank=True)
    multi_lg_corte1 = models.DecimalField(verbose_name="Multiplicador Lg. Corte (Fora do Vão)", max_digits=10, decimal_places=2, default=1, null=True, blank=True)
    multi_lg_corte2 = models.DecimalField(verbose_name="Multiplicador Lg. Corte (Dentro do Vão)", max_digits=10, decimal_places=2, default=1, null=True, blank=True)
    multi_lg_corte3 = models.DecimalField(verbose_name="Multiplicador Lg. Corte (1 Lado do Vão)", max_digits=10, decimal_places=2, default=1, null=True, blank=True)

class FilialContato(models.Model):
    filial = models.OneToOneField('filiais.Filial', on_delete=models.CASCADE, related_name='contato')
    celular = models.CharField(max_length=20, blank=True, null=True)
    whatsapp = models.CharField(max_length=20, blank=True, null=True)
    site = models.URLField(blank=True, null=True)
    instagram = models.CharField(max_length=80, blank=True, null=True)
    facebook = models.CharField(max_length=80, blank=True, null=True)
    email_financeiro = models.EmailField(blank=True, null=True)
    email_fiscal = models.EmailField( blank=True, null=True)
    email_comercial = models.EmailField(blank=True, null=True)

class FilialEstoque(models.Model):
    filial = models.OneToOneField('filiais.Filial', on_delete=models.CASCADE, related_name='estoque')
    controla_lote = models.BooleanField(default=False)
    controla_validade = models.BooleanField(default=False)
    ativar_alerta_estoque = models.BooleanField(default=False)
    estoque_padrao = models.ForeignKey('estoques.Estoque', on_delete=models.SET_NULL, null=True, blank=True)

class FilialImpressao(models.Model):
    filial = models.OneToOneField('filiais.Filial', on_delete=models.CASCADE, related_name='impressao')
    imprimir_logo = models.BooleanField(default=True)
    imp_recibo_cr = models.CharField(max_length=20, verbose_name="Questionar Imp. de Recibo", choices=[('Sim','Sim'), ('Não', 'Não'), ('Auto', 'Auto')], default='Sim')
    imp_recibo_cp = models.CharField(max_length=20, verbose_name="Questionar Imp. de Recibo", choices=[('Sim','Sim'), ('Não', 'Não'), ('Auto', 'Auto')], default='Sim')

class FilialObservacao(models.Model):
    filial = models.OneToOneField('filiais.Filial', on_delete=models.CASCADE, related_name='observacoes')
    obs_pedido = models.TextField(blank=True, null=True)
    observacao_nfe = models.ForeignKey('informacoes.Informacoes', null=True, blank=True, on_delete=models.SET_NULL)
    observacao_boleto = models.TextField(blank=True, null=True)

def caminho_foto_usuario(instance, filename):
    ext = filename.split('.')[-1]
    return f"foto_usuario/foto_{instance.pk}.{ext}"

class Usuario(AbstractUser):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="usuarios", null=True, blank=True)
    username = models.CharField(max_length=150)
    filial_user = models.ForeignKey(Filial, on_delete=models.SET_NULL, null=True, blank=True, related_name="usuarios")
    codigo_local = models.PositiveIntegerField(blank=True, null=True)
    gerar_senha_lib = models.BooleanField(default=False, verbose_name='Gerar Senha de Liberação')
    senha_liberacao = models.CharField(max_length=255, blank=True, null=True, verbose_name='Senha de Liberação', help_text="Para nova senha, preencha esse campo!")
    is_master = models.BooleanField(default=False)
    tel = models.CharField(max_length=20, blank=True, verbose_name="Telefone", null=True)
    foto = models.ImageField(upload_to=caminho_foto_usuario, blank=True, null=True,)
    desconto_maximo = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    limite_credito = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    formas_pagamento = models.ManyToManyField('formas_pgto.FormaPgto', blank=True, related_name="formas_usuario")
    tabelas_preco = models.ManyToManyField('tabelas_preco.TabelaPreco', blank=True, related_name="tabelas_usuario")
    filiais_permitidas = models.ManyToManyField('filiais.Filial', blank=True, related_name="filiais_usuario")
    vendedor = models.ForeignKey('vendedores.Vendedor', on_delete=models.SET_NULL, null=True, blank=True)
    opfilial = models.CharField(max_length=10, verbose_name="Acessar todas as filiais", choices=[('0', 'Não'), ('1', 'Sim')], default="1")
    opformas = models.CharField(max_length=10, verbose_name="Utilizar todas as formas de pagamento", choices=[('0', 'Não'), ('1', 'Sim')], default="1")
    optabelas = models.CharField(max_length=10, verbose_name="Utilizar todas as tabelas de preço", choices=[('0', 'Não'), ('1', 'Sim')], default="1")
    # Alertas
    receber_alerta_estoque = models.BooleanField(default=False)
    receber_alerta_estoque_maximo = models.BooleanField(default=False)
    # Cards
    ver_res_orc = models.BooleanField(default=False)
    ver_res_orc_tec = models.BooleanField(default=False)
    ver_conv_orc = models.BooleanField(default=False)
    ver_ticket_medio = models.BooleanField(default=False)
    ver_valor_perdido = models.BooleanField(default=False)
    ver_vl_total_faturado = models.BooleanField(default=False)
    ver_tempo_medio_faturamento = models.BooleanField(default=False)
    ver_m2_total = models.BooleanField(default=False)
    ver_peso_total = models.BooleanField(default=False)
    ver_situacao_orcamentos = models.BooleanField(default=False)
    ver_evolucao_orcamentos = models.BooleanField(default=False)
    ver_ranking_tecnicos = models.BooleanField(default=False)
    ver_ranking_clientes = models.BooleanField(default=False)
    ver_situacao_valor_orcamentos = models.BooleanField(default=False)
    ver_faturamento_diario = models.BooleanField(default=False)
    ver_top_10_produtos_qtde = models.BooleanField(default=False)
    ver_top_10_produtos_vl = models.BooleanField(default=False)
    ver_formas_orcamentos = models.BooleanField(default=False)
    ver_status_orcamentos = models.BooleanField(default=False)
    ver_cores_orcamentos = models.BooleanField(default=False)
    ver_caracteristicas_orcamentos = models.BooleanField(default=False)

    class Meta:
        unique_together = ('username', 'empresa')
    def save(self, *args, **kwargs):
        if self.pk:
            antiga = Usuario.objects.get(pk=self.pk)
            if antiga.foto and self.foto != antiga.foto:
                if default_storage.exists(antiga.foto.name):
                    default_storage.delete(antiga.foto.name)
        if self.empresa and not self.codigo_local:
            ultimo = Usuario.objects.filter(empresa=self.empresa).aggregate(models.Max('codigo_local'))['codigo_local__max'] or 0
            self.codigo_local = ultimo + 1
        super().save(*args, **kwargs)
    def __str__(self):
        if self.empresa:
            if self.filial_user: return f"{self.username} - Emp: {self.empresa.fantasia}/Filial P.: {self.filial_user.fantasia}"
            return f"{self.username} - Emp: {self.empresa.fantasia}"
        return f"{self.username} (GLOBAL)"

class LogUsuario(models.Model):
    TIPOS = (
        ("CRIAR", "Criou"), ("ALTERAR", "Alterou"), ("EXCLUIR", "Excluiu"), ("FATURAR", "Faturou"), ("CANCELAR", "Cancelou"), ("BAIXA", "Baixa Financeira"),
        ("ESTORNO", "Estorno"), ("ABERTURA", "Abriu Caixa"), ("FECHAMENTO", "Fechou Caixa"), ("LOGIN", "Login"), ("LOGOUT", "Logout"), ("OUTRO", "Outro"),
    )
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="logs")
    empresa = models.ForeignKey("empresas.Empresa", on_delete=models.CASCADE)
    filial = models.ForeignKey("filiais.Filial", on_delete=models.SET_NULL, null=True, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    modulo = models.CharField(max_length=50)
    objeto = models.CharField(max_length=200)
    objeto_id = models.PositiveIntegerField(null=True, blank=True)
    descricao = models.TextField()
    alteracoes = models.JSONField(null=True, blank=True, verbose_name="Alterações")
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data']