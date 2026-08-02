from decimal import Decimal
from django import forms
from django.contrib.auth import authenticate
from .models import Filial, FilialFinanceiro, FilialFiscal, FilialOrcamento, FilialContato, FilialEstoque, FilialImpressao, FilialObservacao
from bancos.models import Banco
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado
from django.contrib.auth import get_user_model
from empresas.models import Empresa
from clientes.models import Cliente
from tecnicos.models import Tecnico
from estoques.models import Estoque
from informacoes.models import Informacoes
from tabelas_preco.models import TabelaPreco
from vendedores.models import Vendedor
Usuario = get_user_model()
from util.parse_decimal import parse_decimal

class EmpresaLoginForm(forms.Form):
    empresa_login = forms.IntegerField(label="ID da Empresa", widget=forms.NumberInput(attrs={'class': 'form-control'}))
    username = forms.CharField(label="Usuário", widget=forms.TextInput(attrs={'class': 'form-control text-lowercase'}))
    password = forms.CharField(label="Senha", widget=forms.PasswordInput)
    def clean(self):
        cleaned_data = super().clean()
        empresa_login = cleaned_data.get("empresa_login")
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")
        if not all([empresa_login, username, password]): return cleaned_data
        try:
            empresa = Empresa.objects.filter(id=empresa_login, situacao='Ativa', contrato__situacao='Ativo').distinct().first()
            if not empresa: raise forms.ValidationError("Empresa não encontrada, inativa ou sem contrato ativo.")
        except Empresa.DoesNotExist: raise forms.ValidationError("Empresa não encontrada ou inativa.")
        user = authenticate(request=self.request if hasattr(self, 'request') else None, username=username.strip().lower(), password=password, empresa_id=empresa.id)
        if user is None: raise forms.ValidationError("Usuário, senha ou empresa incorretos.")
        cleaned_data["user"] = user
        cleaned_data["empresa_login"] = empresa
        return cleaned_data

c = 'form-control form-control-sm border-dark-subtle focus-ring focus-ring-dark'
s = 'form-select form-select-sm border-dark-subtle focus-ring focus-ring-dark'

class FilialForm(forms.ModelForm):
    situacao = forms.ChoiceField(label="Situação", choices=[('Ativa', 'Ativa'), ('Inativa', 'Inativa')], widget=forms.Select(attrs={'class': f'{s}'}))
    cnpj = forms.CharField(label='CNPJ', widget=forms.TextInput(attrs={'class': f'{c}'}))
    ie = forms.CharField(label='Inscrição Estadual', required=False, widget=forms.TextInput(attrs={'class': f'{c}'}))
    razao_social = forms.CharField(label='Razão Social', widget=forms.TextInput(attrs={'class': f'{c} text-uppercase'}))
    fantasia = forms.CharField(label='Fantasia', widget=forms.TextInput(attrs={'class': f'{c} text-uppercase'}))
    endereco = forms.CharField(label='Endereço', widget=forms.TextInput(attrs={'class': f'{c} text-uppercase'}))
    cep = forms.CharField(label='CEP', widget=forms.TextInput(attrs={'class': f'{c}'}))
    bairro_fil = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Bairro')
    complem = forms.CharField(label='Complemento', required=False, widget=forms.TextInput(attrs={'class': f'{c} text-uppercase'}))
    cidade_fil = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Cidade')
    uf = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Estado')
    numero = forms.CharField(label='Nº', widget=forms.TextInput(attrs={'class': f'{c}'}))
    tel = forms.CharField(label="Fone", max_length=20, widget=forms.TextInput(attrs={'maxlength': '20', 'class': f'{c}'}))
    dt_criacao = forms.CharField(label='Dt. Criação', required=False, widget=forms.TextInput(attrs={'class': f'{c} text-lowercase bg-secondary', 'readonly': 'readonly'}))
    cli = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Cliente Padrão')
    tec = forms.ChoiceField(required=False, widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Técnico Padrão')
    tb_preco = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Tabela de Preço Padrão')
    vendedor = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Vendedor Padrão')
    agrupa_itens = forms.ChoiceField(label="Agrupar Itens", choices=[(True, 'Sim'), (False, 'Não')], widget=forms.Select(attrs={'class': f'{s}'}))
    
    def _parse_decimal(self, valor):
        if valor in [None, '']: return Decimal('0.00')
        valor = str(valor).strip()
        valor = valor.replace('.', '').replace(',', '.')
        return Decimal(valor)
    def clean_multi_m2(self):
        return self._parse_decimal(self.cleaned_data['multi_m2'])
    def clean_multi_lg_corte1(self):
        return self._parse_decimal(self.cleaned_data['multi_lg_corte1'])
    def clean_multi_lg_corte2(self):
        return self._parse_decimal(self.cleaned_data['multi_lg_corte2'])
    def clean_multi_lg_corte3(self):
        return self._parse_decimal(self.cleaned_data['multi_lg_corte3'])
    def clean_ft_juros(self):
        return self._parse_decimal(self.cleaned_data['ft_juros'])
    def clean_ft_multa(self):
        return self._parse_decimal(self.cleaned_data['ft_multa'])
    class Meta:
        model = Filial
        fields = (
            'situacao', 'cnpj', 'ie', 'razao_social', 'fantasia', 'cep', 'endereco', 'numero', 'bairro_fil', 'cidade_fil', 'uf', 'tel', 'logo',
            'cli', 'tec', 'vendedor', 'tb_preco', 'vendedor', 'agrupa_itens'
        )
    def __init__(self, *args, **kwargs):
        # Captura e remove a empresa dos kwargs de forma segura
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if not self.empresa and self.instance and self.instance.pk and self.instance.vinc_emp:
            self.empresa = self.instance.vinc_emp
        if self.empresa:
            bairros = Bairro.objects.filter(vinc_emp=self.empresa)
            cidades = Cidade.objects.filter(vinc_emp=self.empresa)
            estados = Estado.objects.filter(vinc_emp=self.empresa)
            clientes = Cliente.objects.filter(vinc_emp=self.empresa)
            tecnicos = Tecnico.objects.filter(vinc_emp=self.empresa)
            tabelas = TabelaPreco.objects.filter(vinc_emp=self.empresa)
            vendedores = Vendedor.objects.filter(vinc_emp=self.empresa)
            self.fields['bairro_fil'].choices = [('', 'Escolha uma opção')] + [(str(b.codigo), b.nome_bairro.upper()) for b in bairros]
            self.fields['cidade_fil'].choices = [('', 'Escolha uma opção')] + [(str(c.codigo), c.nome_cidade.upper()) for c in cidades]
            self.fields['uf'].choices = [('', 'Escolha uma opção')] + [(str(e.codigo), e.nome_estado.upper()) for e in estados]
            self.fields['cli'].choices = [('', 'Escolha uma opção')] + [(str(c.codigo), c.fantasia.upper()) for c in clientes]
            self.fields['tec'].choices = [('', 'Escolha uma opção')] + [(str(t.codigo), t.nome.upper()) for t in tecnicos]
            self.fields['tb_preco'].choices = [('', 'Escolha uma opção')] + [(str(t.codigo), t.descricao.upper()) for t in tabelas]
            self.fields['vendedor'].choices = [('', 'Escolha uma opção')] + [(str(v.codigo), v.fantasia.upper()) for v in vendedores]
            if self.instance and self.instance.pk:
                if self.instance.bairro_fil: self.initial['bairro_fil'] = str(self.instance.bairro_fil.codigo)
                if self.instance.cidade_fil: self.initial['cidade_fil'] = str(self.instance.cidade_fil.codigo)
                if self.instance.uf: self.initial['uf'] = str(self.instance.uf.codigo)
                if self.instance.cli: self.initial['cli'] = str(self.instance.cli.codigo)
                if self.instance.tec: self.initial['tec'] = str(self.instance.tec.codigo)
                if self.instance.tb_preco: self.initial['tb_preco'] = str(self.instance.tb_preco.codigo)
                if self.instance.vendedor: self.initial['vendedor'] = str(self.instance.vendedor.codigo)
        else:
            self.fields['bairro_fil'].choices = [('', 'Escolha uma opção')]
            self.fields['cidade_fil'].choices = [('', 'Escolha uma opção')]
            self.fields['uf'].choices = [('', 'Escolha uma opção')]
            self.fields['cli'].choices = [('', 'Escolha uma opção')]
            self.fields['tec'].choices = [('', 'Escolha uma opção')]
            self.fields['tb_preco'].choices = [('', 'Escolha uma opção')]
            self.fields['vendedor'].choices = [('', 'Escolha uma opção')]
        if getattr(self.instance, 'pk', None):
            if getattr(self.instance, 'dt_criacao', None):
                self.initial['dt_criacao'] = self.instance.dt_criacao.strftime('%d/%m/%Y')
        campos_decimais = ['multi_m2', 'multi_lg_corte1', 'multi_lg_corte2', 'multi_lg_corte3', 'ft_juros', 'ft_multa']
        for campo in campos_decimais:
            valor = getattr(self.instance, campo, None)
            if valor is not None:
                self.fields[campo].initial = f"{valor:.2f}".replace('.', ',')
    def clean(self):
        cleaned_data = super().clean()
        # Mapeamento genérico: 'nome_no_form': (ClasseDoModel, 'Nome Amigável para o Erro')
        campos_select2 = {
            'bairro_fil': (Bairro, 'Bairro'),
            'cidade_fil': (Cidade, 'Cidade'),
            'uf': (Estado, 'UF'),
            'cli': (Cliente, 'Cliente Padrão'),
            'tec': (Tecnico, 'Técnico Padrão'),
            'tb_preco': (TabelaPreco, 'Tabela de Preço Padrão'),
            'vendedor': (Vendedor, 'Vendedor Padrão')
        }
        for nome_campo, (model_classe, nome_exibicao) in campos_select2.items():
            codigo = cleaned_data.get(nome_campo)
            # Se o usuário preencheu o campo (não é None e nem string vazia)
            if codigo and codigo != '':
                try:
                    objeto_real = model_classe.objects.get(codigo=codigo, vinc_emp=self.empresa)
                    cleaned_data[nome_campo] = objeto_real  # Substitui pelo objeto do banco
                except model_classe.DoesNotExist:
                    self.add_error(nome_campo, f"{nome_exibicao} inválido(a) para esta empresa.")
            else:
                # ✅ CORREÇÃO: Se veio vazio ou '', força a ser None para o Django salvar como NULL
                cleaned_data[nome_campo] = None
        return cleaned_data

class FilialFinanceiroForm(forms.ModelForm):
    tp_chave = forms.ChoiceField(label="Tipo de Chave", choices=[('', ''), ('CPF', 'CPF'), ('CNPJ', 'CNPJ'), ('E-mail', 'E-mail'), ('Telefone', 'Telefone'), ('Chave Aleatória', 'Chave Aleatória')], required=False, widget=forms.Select(attrs={'class': f'{s}'}))
    banco_fil = forms.ChoiceField(required=False, widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Banco')
    beneficiario = forms.CharField(label='Beneficiário', required=False, widget=forms.TextInput(attrs={'class': f'{c} text-uppercase'}))
    chave_pix = forms.CharField(label='Chave Pix', required=False, widget=forms.TextInput(attrs={'class': f'{c} text-lowercase'}))
    max_parcelas = forms.DecimalField(label='', max_digits=10, decimal_places=2, widget=forms.TextInput(attrs={'type': 'number', 'class': f'{c} text-end fw-bold'}))
    max_dias_intervalo = forms.DecimalField(label='', max_digits=10, decimal_places=2, widget=forms.TextInput(attrs={'type': 'number', 'class': f'{c} text-end fw-bold'}))
    tp_calc_juros = forms.ChoiceField(label="Tp. Cálculo Juros", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], widget=forms.Select(attrs={'class': f'{s}'}))
    tp_calc_multa = forms.ChoiceField(label="Tp. Cálculo Multa", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], widget=forms.Select(attrs={'class': f'{s}'}))
    ft_juros = forms.CharField(label='Fator Juros', widget=forms.TextInput(attrs={'class': f'{c} text-end fw-bold'}))
    ft_multa = forms.CharField(label='Fator Multa', widget=forms.TextInput(attrs={'class': f'{c} text-end fw-bold'}))
    desconto_maximo = forms.CharField(label='Desconto Máximo %', widget=forms.TextInput(attrs={'class': f'{c} text-end fw-bold'}))
    acrescimo_maximo = forms.CharField(label='Acréscimo Máximo %', widget=forms.TextInput(attrs={'class': f'{c} text-end fw-bold'}))
    limite_credito_padrao = forms.CharField(label='Limite Crédito Máximo', widget=forms.TextInput(attrs={'class': f'{c} text-end fw-bold'}))
    
    class Meta:
        model = FilialFinanceiro
        exclude = ("filial",)

    def __init__(self, *args, **kwargs):
        # Captura e remove a empresa dos kwargs de forma segura
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if not self.empresa and self.instance and self.instance.pk and self.instance.empresa:
            self.empresa = self.instance.empresa
        if self.empresa:
            bancos = Banco.objects.filter(vinc_emp=self.empresa)
            self.fields['banco_fil'].choices = [('', 'Escolha uma opção')] + [(str(b.codigo), b.nome_banco.upper()) for b in bancos]
            if self.instance and self.instance.pk:
                if self.instance.banco_fil: self.initial['banco_fil'] = str(self.instance.banco_fil.codigo)
        else:
            self.fields['banco_fil'].choices = [('', 'Escolha uma opção')]

    def clean(self):
        cleaned_data = super().clean()
        campos_select2 = {
            'banco_fil': (Estoque, 'Banco'),
        }
        for nome_campo, (model_classe, nome_exibicao) in campos_select2.items():
            codigo = cleaned_data.get(nome_campo)
            # Se o usuário preencheu o campo (não é None e nem string vazia)
            if codigo and codigo != '':
                try:
                    objeto_real = model_classe.objects.get(codigo=codigo, empresa=self.empresa)
                    cleaned_data[nome_campo] = objeto_real  # Substitui pelo objeto do banco
                except model_classe.DoesNotExist:
                    self.add_error(nome_campo, f"{nome_exibicao} inválido(a) para esta empresa.")
            else:
                # ✅ CORREÇÃO: Se veio vazio ou '', força a ser None para o Django salvar como NULL
                cleaned_data[nome_campo] = None
        try: cleaned_data['ft_juros'] = parse_decimal(cleaned_data.get('ft_juros'))
        except: self.add_error('ft_juros', 'Valor inválido.')
        try: cleaned_data['ft_multa'] = parse_decimal(cleaned_data.get('ft_multa'))
        except: self.add_error('ft_multa', 'Valor inválido.')
        try: cleaned_data['desconto_maximo'] = parse_decimal(cleaned_data.get('desconto_maximo'))
        except: self.add_error('desconto_maximo', 'Valor inválido.')
        try: cleaned_data['acrescimo_maximo'] = parse_decimal(cleaned_data.get('acrescimo_maximo'))
        except: self.add_error('acrescimo_maximo', 'Valor inválido.')
        try: cleaned_data['limite_credito_padrao'] = parse_decimal(cleaned_data.get('limite_credito_padrao'))
        except: self.add_error('limite_credito_padrao', 'Valor inválido.')
        return cleaned_data

class FilialFiscalForm(forms.ModelForm):
    crt = forms.ChoiceField(label="CRT", choices=[('1', 'Simples Nacional'), ('2', 'Simples Nacional Excesso'), ('3', 'Regime Normal')], required=False, widget=forms.Select(attrs={'class': f'{s}'}))
    im = forms.CharField(label='Inscrição Municipal', required=False, widget=forms.TextInput(attrs={'class': f'{c}'}))
    suframa = forms.CharField(label='SUFRAMA', required=False, widget=forms.TextInput(attrs={'class': f'{c}'}))
    senha_certificado = forms.CharField(label='Senha Certificado', required=False, widget=forms.TextInput(attrs={'class': f'{c}', 'type': 'password'}))
    serie_nfe = forms.DecimalField(label='Série NF-e', required=False, max_digits=10, decimal_places=2, widget=forms.TextInput(attrs={'type': 'number', 'class': f'{c} text-end fw-bold'}))
    serie_nfce = forms.DecimalField(label='Série NFC-e', required=False, max_digits=10, decimal_places=2, widget=forms.TextInput(attrs={'type': 'number', 'class': f'{c} text-end fw-bold'}))
    ultimo_numero_nfe = forms.DecimalField(label='Último Nº NF-e', required=False, max_digits=10, decimal_places=2, widget=forms.TextInput(attrs={'type': 'number', 'class': f'{c} text-end fw-bold'}))
    ultimo_numero_nfce = forms.DecimalField(label='Último Nº NFC-e', required=False, max_digits=10, decimal_places=2, widget=forms.TextInput(attrs={'type': 'number', 'class': f'{c} text-end fw-bold'}))
    ambiente_fiscal = forms.ChoiceField(label="Ambiente", choices=[('Homologação', 'Homologação'), ('Produção', 'Produção')], required=False, widget=forms.Select(attrs={'class': f'{s}'}))
    cnae_principal = forms.CharField(label='CNAE Principal', required=False, widget=forms.TextInput(attrs={'class': f'{c}'}))
    csc = forms.CharField(label='CSC', required=False, widget=forms.TextInput(attrs={'class': f'{c}'}))
    cod_csc = forms.CharField(label='ID CSC', required=False, widget=forms.TextInput(attrs={'class': f'{c}'}))

    class Meta:
        model = FilialFiscal
        exclude = ("filial",)

    def __init__(self, *args, **kwargs):
        # Captura e remove a empresa dos kwargs de forma segura
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        self.fields['certificado'].widget.attrs.update({
            'accept': '.pfx,.p12'
        })

class FilialOrcamentoForm(forms.ModelForm):
    layout_contrato = forms.ChoiceField(label="Layout Contrato", choices=[('Layout 1', 'Layout 1'), ('Layout 2', 'Layout 2')], widget=forms.Select(attrs={'class': f'{s}'}))
    layout_prod = forms.ChoiceField(label="L. PDF Produção", choices=[('1', 'Layout 1'), ('2', 'Layout 2')], widget=forms.Select(attrs={'class': f'{s}'}))
    imp_recibo_orc = forms.ChoiceField(label="", choices=[('Sim', 'Sim'), ('Não', 'Não'), ('Auto', 'Auto')], widget=forms.Select(attrs={'class': f'{s}'}))
    info_comp = forms.CharField(label='Informações Rodapé - Comprovantes', required=False, widget=forms.Textarea(attrs={'class': f'{c}', 'rows': 2}))
    info_local = forms.CharField(label='Info. Local Atendimento - Propostas', required=False, widget=forms.Textarea(attrs={'class': f'{c}', 'rows': 2}))
    info_orcamento = forms.CharField(label='Informações Rodapé - Orçamento', required=False, widget=forms.Textarea(attrs={'class': f'{c}', 'rows': 2}))
    mt_qt_lam = forms.CharField(label='', help_text="larg: Largura, alt: Altura, larg_corte: Largura de Corte, alt_corte: Altura de Corte, qtd_laminas: Qtde. de Lâminas, m2: M², ft_peso: Fator de Peso, peso: Peso, rolo: Rolo.", widget=forms.TextInput(attrs={'class': f'{c} text-end fw-bold'}))
    multi_m2 = forms.CharField(label='', widget=forms.TextInput(attrs={'class': f'{c} text-end fw-bold'}))
    multi_lg_corte1 = forms.CharField(label='', widget=forms.TextInput(attrs={'class': f'{c} text-end fw-bold'}))
    multi_lg_corte2 = forms.CharField(label='', widget=forms.TextInput(attrs={'class': f'{c} text-end fw-bold'}))
    multi_lg_corte3 = forms.CharField(label='', widget=forms.TextInput(attrs={'class': f'{c} text-end fw-bold'}))

    class Meta:
        model = FilialOrcamento
        exclude = ("filial",)
    
    def __init__(self, *args, **kwargs):
        # Captura e remove a empresa dos kwargs de forma segura
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        try: cleaned_data['multi_m2'] = parse_decimal(cleaned_data.get('multi_m2'))
        except: self.add_error('multi_m2', 'Valor inválido.')
        try: cleaned_data['multi_lg_corte1'] = parse_decimal(cleaned_data.get('multi_lg_corte1'))
        except: self.add_error('multi_lg_corte1', 'Valor inválido.')
        try: cleaned_data['multi_lg_corte2'] = parse_decimal(cleaned_data.get('multi_lg_corte2'))
        except: self.add_error('multi_lg_corte2', 'Valor inválido.')
        try: cleaned_data['multi_lg_corte3'] = parse_decimal(cleaned_data.get('multi_lg_corte3'))
        except: self.add_error('multi_lg_corte3', 'Valor inválido.')
        return cleaned_data

class FilialContatoForm(forms.ModelForm):
    celular = forms.CharField(label="Celular", required=False, max_length=20, widget=forms.TextInput(attrs={'maxlength': '20', 'class': f'{c}'}))
    whatsapp = forms.CharField(label="Whatsapp", required=False, max_length=20, widget=forms.TextInput(attrs={'maxlength': '20', 'class': f'{c}'}))
    site = forms.URLField(label='Site', required=False, widget=forms.URLInput(attrs={'class': c}))
    email_financeiro = forms.CharField(label='E-mail Financeiro', required=False, widget=forms.TextInput(attrs={'class': f'{c} text-lowercase'}))
    email_fiscal = forms.CharField(label='E-mail Fiscal', required=False, widget=forms.TextInput(attrs={'class': f'{c} text-lowercase'}))
    email_comercial = forms.CharField(label='E-mail Comercial', required=False, widget=forms.TextInput(attrs={'class': f'{c} text-lowercase'}))
    instagram = forms.CharField(label="Instagram", required=False, max_length=20, widget=forms.TextInput(attrs={'maxlength': '20', 'class': f'{c}'}))
    facebook = forms.CharField(label="Facebook", required=False, max_length=20, widget=forms.TextInput(attrs={'maxlength': '20', 'class': f'{c}'}))

    def __init__(self, *args, **kwargs):
        # Captura e remove a empresa dos kwargs de forma segura
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = FilialContato
        exclude = ("filial",)

class FilialEstoqueForm(forms.ModelForm):
    controla_lote = forms.ChoiceField(label="Controla Lote?", choices=[(True, 'Sim'), (False, 'Não')], widget=forms.Select(attrs={'class': f'{s}'}))
    controla_validade = forms.ChoiceField(label="Controla Validade?", choices=[(True, 'Sim'), (False, 'Não')], widget=forms.Select(attrs={'class': f'{s}'}))
    ativar_alerta_estoque = forms.ChoiceField(label="Ativar Alerta Estoque?", choices=[(True, 'Sim'), (False, 'Não')], widget=forms.Select(attrs={'class': f'{s}'}))
    estoque_padrao = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Estoque Padrão')

    class Meta:
        model = FilialEstoque
        exclude = ("filial",)

    def __init__(self, *args, **kwargs):
        # Captura e remove a empresa dos kwargs de forma segura
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if not self.empresa and self.instance and self.instance.pk and self.instance.empresa:
            self.empresa = self.instance.empresa
        if self.empresa:
            estoques = Estoque.objects.filter(empresa=self.empresa)
            self.fields['estoque_padrao'].choices = [('', 'Escolha uma opção')] + [(str(e.codigo), e.descricao.upper()) for e in estoques]
            if self.instance and self.instance.pk:
                if self.instance.estoque_padrao: self.initial['estoque_padrao'] = str(self.instance.estoque_padrao.codigo)
        else:
            self.fields['estoque_padrao'].choices = [('', 'Escolha uma opção')]
    def clean(self):
        cleaned_data = super().clean()
        # Mapeamento genérico: 'nome_no_form': (ClasseDoModel, 'Nome Amigável para o Erro')
        campos_select2 = {
            'estoque_padrao': (Estoque, 'Estoque Padrão'),
        }
        for nome_campo, (model_classe, nome_exibicao) in campos_select2.items():
            codigo = cleaned_data.get(nome_campo)
            # Se o usuário preencheu o campo (não é None e nem string vazia)
            if codigo and codigo != '':
                try:
                    objeto_real = model_classe.objects.get(codigo=codigo, empresa=self.empresa)
                    cleaned_data[nome_campo] = objeto_real  # Substitui pelo objeto do banco
                except model_classe.DoesNotExist:
                    self.add_error(nome_campo, f"{nome_exibicao} inválido(a) para esta empresa.")
            else:
                # ✅ CORREÇÃO: Se veio vazio ou '', força a ser None para o Django salvar como NULL
                cleaned_data[nome_campo] = None
        return cleaned_data

class FilialImpressaoForm(forms.ModelForm):
    imprimir_logo = forms.ChoiceField(label="Imprimir Logo", choices=[(True, 'Sim'), (False, 'Não')], widget=forms.Select(attrs={'class': f'{s}'}))
    imp_recibo_cr = forms.ChoiceField(label="", choices=[('Sim', 'Sim'), ('Não', 'Não'), ('Auto', 'Auto')], widget=forms.Select(attrs={'class': f'{s}'}))

    class Meta:
        model = FilialImpressao
        exclude = ("filial",)
    
    def __init__(self, *args, **kwargs):
        # Captura e remove a empresa dos kwargs de forma segura
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)

class FilialObservacaoForm(forms.ModelForm):
    obs_pedido = forms.CharField(label='Informações Rodapé (Pedidos)', required=False, widget=forms.Textarea(attrs={'class': f'{c}', 'rows': 2}))
    observacao_nfe = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Informações Adicionais (NF-e)')
    observacao_boleto = forms.CharField(label='Informações Adicionais (Boletos)', required=False, widget=forms.Textarea(attrs={'class': f'{c}', 'rows': 2}))

    class Meta:
        model = FilialObservacao
        exclude = ("filial",)

    def __init__(self, *args, **kwargs):
        # Captura e remove a empresa dos kwargs de forma segura
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if not self.empresa and self.instance and self.instance.pk and self.instance.empresa:
            self.empresa = self.instance.empresa
        if self.empresa:
            informacoes = Informacoes.objects.filter(empresa=self.empresa)
            self.fields['observacao_nfe'].choices = [('', 'Escolha uma opção')] + [(str(i.codigo), i.descricao.upper()) for i in informacoes]
            if self.instance and self.instance.pk:
                if self.instance.observacao_nfe: self.initial['observacao_nfe'] = str(self.instance.observacao_nfe.codigo)
        else:
            self.fields['observacao_nfe'].choices = [('', 'Escolha uma opção')]
    def clean(self):
        cleaned_data = super().clean()
        # Mapeamento genérico: 'nome_no_form': (ClasseDoModel, 'Nome Amigável para o Erro')
        campos_select2 = {
            'observacao_nfe': (Informacoes, 'Informações Adicionais (NF-e)'),
        }
        for nome_campo, (model_classe, nome_exibicao) in campos_select2.items():
            codigo = cleaned_data.get(nome_campo)
            # Se o usuário preencheu o campo (não é None e nem string vazia)
            if codigo and codigo != '':
                try:
                    objeto_real = model_classe.objects.get(codigo=codigo, empresa=self.empresa)
                    cleaned_data[nome_campo] = objeto_real  # Substitui pelo objeto do banco
                except model_classe.DoesNotExist:
                    self.add_error(nome_campo, f"{nome_exibicao} inválido(a) para esta empresa.")
            else:
                # ✅ CORREÇÃO: Se veio vazio ou '', força a ser None para o Django salvar como NULL
                cleaned_data[nome_campo] = None
        return cleaned_data
    
class FilialReadOnlyForm(forms.ModelForm):
    class Meta:
        model = Filial
        fields = (
            'situacao', 'cnpj', 'ie', 'razao_social', 'fantasia', 'cep', 'endereco', 'numero', 'bairro_fil', 'cidade_fil', 'uf', 'tel', 'logo',
            'cli', 'tec', 'vendedor', 'tb_preco', 'vendedor', 'agrupa_itens'
        )
    def __init__(self, *args, empresa=None, **kwargs):
        super(FilialReadOnlyForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.disabled = True