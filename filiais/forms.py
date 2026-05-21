from decimal import Decimal
from django import forms
from django.contrib.auth import authenticate
from .models import Filial
from bancos.models import Banco
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado
from django.contrib.auth import get_user_model
from empresas.models import Empresa
from clientes.models import Cliente
from tecnicos.models import Tecnico
from tabelas_preco.models import TabelaPreco
from vendedores.models import Vendedor
Usuario = get_user_model()

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

c = 'form-control form-control-sm border-dark-subtle'
s = 'form-select form-select-sm border-dark-subtle'

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
    email = forms.CharField(label='E-mail', widget=forms.TextInput(attrs={'class': f'{c} text-lowercase'}))
    tp_chave = forms.ChoiceField(label="Tipo de Chave", choices=[('', ''), ('CPF', 'CPF'), ('CNPJ', 'CNPJ'), ('E-mail', 'E-mail'), ('Telefone', 'Telefone'), ('Chave Aleatória', 'Chave Aleatória')], required=False, widget=forms.Select(attrs={'class': f'{s}'}))
    banco_fil = forms.ChoiceField(required=False, widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Banco')
    beneficiario = forms.CharField(label='Beneficiário', required=False, widget=forms.TextInput(attrs={'class': f'{c} text-uppercase'}))
    chave_pix = forms.CharField(label='Chave Pix', required=False, widget=forms.TextInput(attrs={'class': f'{c} text-lowercase'}))
    dt_criacao = forms.CharField(label='Dt. Criação', required=False, widget=forms.TextInput(attrs={'class': f'{c} text-lowercase bg-secondary', 'readonly': 'readonly'}))
    info_comp = forms.CharField(label='Informações Rodapé - Comprovantes', required=False, widget=forms.Textarea(attrs={'class': f'{c}', 'rows': 2}))
    info_local = forms.CharField(label='Info. Local Atendimento - Propostas', required=False, widget=forms.Textarea(attrs={'class': f'{c}', 'rows': 2}))
    info_orcamento = forms.CharField(label='Informações Rodapé - Orçamento', required=False, widget=forms.Textarea(attrs={'class': f'{c}', 'rows': 2}))
    layout_contrato = forms.ChoiceField(label="Layout Contrato", choices=[('Layout 1', 'Layout 1'), ('Layout 2', 'Layout 2')], widget=forms.Select(attrs={'class': f'{s}'}))
    tp_calc_juros = forms.ChoiceField(label="Tp. Cálculo Juros", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], widget=forms.Select(attrs={'class': f'{s}'}))
    tp_calc_multa = forms.ChoiceField(label="Tp. Cálculo Multa", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], widget=forms.Select(attrs={'class': f'{s}'}))
    ft_juros = forms.CharField(label='Fator Juros', widget=forms.TextInput(attrs={'class': f'{c} text-end fw-bold'}))
    ft_multa = forms.CharField(label='Fator Multa', widget=forms.TextInput(attrs={'class': f'{c} text-end fw-bold'}))
    max_parcelas = forms.DecimalField(label='', max_digits=10, decimal_places=2, widget=forms.TextInput(attrs={'type': 'number', 'class': f'{c} text-end fw-bold'}))
    max_dias_intervalo = forms.DecimalField(label='', max_digits=10, decimal_places=2, widget=forms.TextInput(attrs={'type': 'number', 'class': f'{c} text-end fw-bold'}))
    cli = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Cliente Padrão')
    tec = forms.ChoiceField(required=False, widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Técnico Padrão')
    tb_preco = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Tabela de Preço Padrão')
    vendedor = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Vendedor Padrão')
    multi_m2 = forms.CharField(label='', widget=forms.TextInput(attrs={'class': f'{c} text-end fw-bold'}))
    multi_lg_corte1 = forms.CharField(label='', widget=forms.TextInput(attrs={'class': f'{c} text-end fw-bold'}))
    multi_lg_corte2 = forms.CharField(label='', widget=forms.TextInput(attrs={'class': f'{c} text-end fw-bold'}))
    multi_lg_corte3 = forms.CharField(label='', widget=forms.TextInput(attrs={'class': f'{c} text-end fw-bold'}))
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
            'situacao', 'cnpj', 'ie', 'razao_social', 'fantasia', 'cep', 'endereco', 'numero', 'bairro_fil', 'cidade_fil', 'uf', 'tel', 'email', 'logo', 'tp_chave', 'chave_pix', 'banco_fil', 'info_comp', 'complem',
            'beneficiario', 'info_orcamento', 'layout_contrato', 'info_local', 'tp_calc_juros', 'tp_calc_multa', 'ft_juros', 'ft_multa', 'max_parcelas', 'cli', 'tec', 'vendedor', 'tb_preco', 'max_dias_intervalo', 'vendedor',
            'multi_m2', 'agrupa_itens', 'multi_lg_corte1', 'multi_lg_corte2', 'multi_lg_corte3'
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
            bancos = Banco.objects.filter(vinc_emp=self.empresa)
            clientes = Cliente.objects.filter(vinc_emp=self.empresa)
            tecnicos = Tecnico.objects.filter(vinc_emp=self.empresa)
            tabelas = TabelaPreco.objects.filter(vinc_emp=self.empresa)
            vendedores = Vendedor.objects.filter(vinc_emp=self.empresa)
            self.fields['bairro_fil'].choices = [('', 'Escolha uma opção')] + [(str(b.codigo), b.nome_bairro.upper()) for b in bairros]
            self.fields['cidade_fil'].choices = [('', 'Escolha uma opção')] + [(str(c.codigo), c.nome_cidade.upper()) for c in cidades]
            self.fields['uf'].choices = [('', 'Escolha uma opção')] + [(str(e.codigo), e.nome_estado.upper()) for e in estados]
            self.fields['banco_fil'].choices = [('', 'Escolha uma opçãoo')] + [(str(b.codigo), b.nome_banco.upper()) for b in bancos]
            self.fields['cli'].choices = [('', 'Escolha uma opção')] + [(str(c.codigo), c.fantasia.upper()) for c in clientes]
            self.fields['tec'].choices = [('', 'Escolha uma opção')] + [(str(t.codigo), t.nome.upper()) for t in tecnicos]
            self.fields['tb_preco'].choices = [('', 'Escolha uma opção')] + [(str(t.codigo), t.descricao.upper()) for t in tabelas]
            self.fields['vendedor'].choices = [('', 'Escolha uma opção')] + [(str(v.codigo), v.fantasia.upper()) for v in vendedores]
            if self.instance and self.instance.pk:
                if self.instance.bairro_fil: self.initial['bairro_fil'] = str(self.instance.bairro_fil.codigo)
                if self.instance.cidade_fil: self.initial['cidade_fil'] = str(self.instance.cidade_fil.codigo)
                if self.instance.uf: self.initial['uf'] = str(self.instance.uf.codigo)
                if self.instance.banco_fil: self.initial['banco_fil'] = str(self.instance.banco_fil.codigo)
                if self.instance.cli: self.initial['cli'] = str(self.instance.cli.codigo)
                if self.instance.tec: self.initial['tec'] = str(self.instance.tec.codigo)
                if self.instance.tb_preco: self.initial['tb_preco'] = str(self.instance.tb_preco.codigo)
                if self.instance.vendedor: self.initial['vendedor'] = str(self.instance.vendedor.codigo)
        else:
            self.fields['bairro_fil'].choices = [('', 'Escolha uma opção')]
            self.fields['cidade_fil'].choices = [('', 'Escolha uma opção')]
            self.fields['uf'].choices = [('', 'Escolha uma opção')]
            self.fields['banco_fil'].choices = [('', 'Escolha uma opção')]
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
            'banco_fil': (Banco, 'Banco'),
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

class FilialReadOnlyForm(forms.ModelForm):
    class Meta:
        model = Filial
        fields = (
            'situacao', 'cnpj', 'ie', 'razao_social', 'fantasia', 'cep', 'endereco', 'numero', 'bairro_fil', 'cidade_fil', 'uf', 'tel', 'email', 'dt_criacao', 'logo', 'tp_chave', 'chave_pix', 'banco_fil', 'info_comp', 'complem',
            'beneficiario', 'info_orcamento', 'layout_contrato', 'info_local', 'tp_calc_juros', 'tp_calc_multa', 'ft_juros', 'ft_multa', 'max_parcelas', 'cli', 'tec', 'tb_preco', 'max_dias_intervalo', 'vendedor', 'multi_m2',
            'agrupa_itens', 'multi_lg_corte1', 'multi_lg_corte2', 'multi_lg_corte3'
        )
    def __init__(self, *args, empresa=None, **kwargs):
        super(FilialReadOnlyForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.disabled = True