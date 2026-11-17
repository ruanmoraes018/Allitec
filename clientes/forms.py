from django import forms
from .models import Cliente
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado
from filiais.models import Filial
from datetime import datetime
from util.parse_decimal import parse_decimal

c = "form-control form-control-sm border-dark-subtle"
s = "form-select form-select-sm border-dark-subtle"

class ClienteForm(forms.ModelForm):
    vinc_fil = forms.ChoiceField(widget=forms.Select(attrs={'class': s}), label='Filial')
    situacao = forms.ChoiceField(label="Situação", choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')], widget=forms.Select(attrs={'class': s}))
    somente_avista = forms.ChoiceField(label="Vender somente à vista", choices=[(True, 'Sim'), (False, 'Não')], widget=forms.Select(attrs={'class': s}))
    pessoa = forms.ChoiceField(label="Pessoa", choices=[('Física', 'Física'), ('Jurídica', 'Jurídica')], widget=forms.Select(attrs={'class': s}))
    cpf_cnpj = forms.CharField(label='CPF', widget=forms.TextInput(attrs={'class': c}))
    ie = forms.CharField(label='RG', required=False, widget=forms.TextInput(attrs={'class': c}))
    ie_st = forms.CharField(label='IE ST', required=False, widget=forms.TextInput(attrs={'class': c}))
    im = forms.CharField(label='Insc. Municipal', required=False, widget=forms.TextInput(attrs={'class': c}))
    suframa = forms.CharField(label='SUFRAMA', required=False, widget=forms.TextInput(attrs={'class': c}))
    cnae = forms.CharField(label='CNAE', required=False, widget=forms.TextInput(attrs={'class': c}))
    ind_ie = forms.ChoiceField(label="Indicador IE", choices=[('1', 'Contribuinte'), ('2', 'Isento'), ('9', 'Não contribuinte')], widget=forms.Select(attrs={'class': s}))
    regime_tributario = forms.ChoiceField(label="Regime Tributário", choices=[('1', 'Simples Nacional'), ('2', 'Simples Nacional – Excesso de Sublimite'), ('3', 'Regime Normal')], widget=forms.Select(attrs={'class': s}))
    razao_social = forms.CharField(label='Razão Social', widget=forms.TextInput(attrs={'class': f'{c} text-uppercase'}))
    fantasia = forms.CharField(label='Fantasia', widget=forms.TextInput(attrs={'class': f'{c} text-uppercase'}))
    endereco = forms.CharField(label='Endereço', widget=forms.TextInput(attrs={'class': f'{c} text-uppercase'}))
    cep = forms.CharField(label='CEP', widget=forms.TextInput(attrs={'class': c}))
    complem = forms.CharField(label='Complemento', required=False, widget=forms.TextInput(attrs={'class': f'{c} text-uppercase'}))
    bairro = forms.ChoiceField(widget=forms.Select(attrs={'class': f'{c} text-uppercase'}), label='Bairro')
    cidade = forms.ChoiceField(widget=forms.Select(attrs={'class': f'{c} text-uppercase'}), label='Cidade')
    uf = forms.ChoiceField(widget=forms.Select(attrs={'class': f'{c} text-uppercase'}), label='Estado')
    numero = forms.CharField(label='Nº', widget=forms.TextInput(attrs={'class': c}))
    tel = forms.CharField(label="Fone", max_length=20, widget=forms.TextInput(attrs={'maxlength': '20', 'class': c}))
    tel2 = forms.CharField(label="2º Fone", max_length=20, required=False, widget=forms.TextInput(attrs={'maxlength': '20', 'class': c}))
    limite_credito = forms.CharField(label='Limite Crédito', required=False, widget=forms.TextInput(attrs={'class': c}))
    bloqueado = forms.ChoiceField(label="Bloqueado para Vendas", choices=[(False, 'Não'), (True, 'Sim')], widget=forms.Select(attrs={'class': s}))
    motivo_bloqueio = forms.CharField(label='Motivo Bloqueio', required=False, widget=forms.TextInput(attrs={'class': c}))
    email = forms.CharField(label='E-mail', required=False, widget=forms.TextInput(attrs={'class': f'{c} text-lowercase'}))
    avulso = forms.ChoiceField(label="Cliente Avulso", choices=[(False, 'Não'), (True, 'Sim')], widget=forms.Select(attrs={'class': s}))
    desconto_padrao = forms.CharField(label='Desconto Padrão (%)', required=False, widget=forms.TextInput(attrs={'class': c}))
    dt_nascimento = forms.CharField(label='Dt. Nascimento', required=False, widget=forms.TextInput(attrs={'class': c}))
    dt_fundacao = forms.CharField(label='Dt. Fundação', required=False, widget=forms.TextInput(attrs={'class': c}))
    observacoes = forms.CharField(label='Observações', required=False, widget=forms.Textarea(attrs={'class': f'{c} text-uppercase', 'rows': 2}))
    class Meta:
        model = Cliente
        exclude = ('codigo', 'vinc_emp', 'dt_reg', 'dt_ult_compra')
    def __init__(self, *args, **kwargs):
        # Captura e remove a empresa dos kwargs de forma segura
        self.empresa = kwargs.pop('empresa', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if not self.empresa and self.instance and self.instance.pk and getattr(self.instance, 'vinc_emp', None):
            self.empresa = self.instance.vinc_emp
        if self.empresa:
            bairros = Bairro.objects.filter(vinc_emp=self.empresa)
            cidades = Cidade.objects.filter(vinc_emp=self.empresa)
            estados = Estado.objects.filter(vinc_emp=self.empresa)
            filiais = Filial.objects.filter(vinc_emp=self.empresa)
            self.fields['bairro'].choices = [('', 'Escolha um Bairro')] + [(str(b.codigo), b.nome_bairro.upper()) for b in bairros]
            self.fields['cidade'].choices = [('', 'Escolha uma Cidade')] + [(str(c.codigo), c.nome_cidade.upper()) for c in cidades]
            self.fields['uf'].choices = [('', 'Escolha um Estado')] + [(str(e.codigo), e.nome_estado.upper()) for e in estados]
            self.fields['vinc_fil'].choices = [('', 'Escolha uma Filial')] + [(str(f.codigo), f.fantasia.upper()) for f in filiais]
            # Define os valores iniciais em caso de Edição (Uso do código)
            if self.instance and self.instance.pk:
                if self.instance.bairro: self.initial['bairro'] = str(self.instance.bairro.codigo)
                if self.instance.cidade: self.initial['cidade'] = str(self.instance.cidade.codigo)
                if self.instance.uf: self.initial['uf'] = str(self.instance.uf.codigo)
                if self.instance.vinc_fil: self.initial['vinc_fil'] = str(self.instance.vinc_fil.codigo)
                if self.instance.dt_nascimento: self.initial['dt_nascimento'] = self.instance.dt_nascimento.strftime('%d/%m/%Y')
                if self.instance.dt_fundacao: self.initial['dt_fundacao'] = self.instance.dt_fundacao.strftime('%d/%m/%Y')
            else:
                # ✅ Se for CRIAÇÃO (Novo Registro): Pré-seleciona a filial do usuário logado
                if self.user and self.user.filial_user:
                    self.initial['vinc_fil'] = str(self.user.filial_user.codigo)
        else:
            self.fields['bairro'].choices = [('', 'Escolha um Bairro')]
            self.fields['cidade'].choices = [('', 'Escolha uma Cidade')]
            self.fields['uf'].choices = [('', 'Escolha um Estado')]
            self.fields['vinc_fil'].choices = [('', 'Escolha uma Filial')]
        if getattr(self.instance, 'pk', None):
            if getattr(self.instance, 'dt_nascimento', None): self.initial['dt_nascimento'] = self.instance.dt_nascimento.strftime('%d/%m/%Y')
            if getattr(self.instance, 'dt_fundacao', None): self.initial['dt_fundacao'] = self.instance.dt_fundacao.strftime('%d/%m/%Y')

    def clean(self):
        cleaned_data = super().clean()
        # Converte datas do formato DD/MM/YYYY para date
        for campo in ['dt_nascimento', 'dt_fundacao']:
            valor = cleaned_data.get(campo)
            if valor:
                try: cleaned_data[campo] = datetime.strptime(valor, '%d/%m/%Y').date()
                except ValueError: self.add_error(campo,'Data inválida. Use o formato DD/MM/AAAA.')
        c_d = ['desconto_padrao', 'limite_credito']
        for c in c_d:
            try: cleaned_data[c] = parse_decimal(cleaned_data.get(c))
            except: self.add_error(c, 'Valor inválido.')
        # Mapeamento genérico: 'nome_no_form': (ClasseDoModel, 'Nome Amigável para o Erro')
        campos_select2 = {'bairro': (Bairro, 'Bairro'), 'cidade': (Cidade, 'Cidade'), 'uf': (Estado, 'UF'), 'vinc_fil': (Filial, 'Filial'),}
        for nome_campo, (model_classe, nome_exibicao) in campos_select2.items():
            codigo = cleaned_data.get(nome_campo)
            # Se o usuário preencheu o campo, fazemos a conversão genérica
            if codigo:
                try:
                    objeto_real = model_classe.objects.get(codigo=codigo, vinc_emp=self.empresa)
                    cleaned_data[nome_campo] = objeto_real  # Substitui o código string pelo objeto do banco
                except model_classe.DoesNotExist:
                    self.add_error(nome_campo, f"{nome_exibicao} inválido(a) para esta empresa.")
        return cleaned_data