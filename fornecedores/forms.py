from django import forms
from .models import Fornecedor
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado

class FornecedorForm(forms.ModelForm):
    situacao = forms.ChoiceField(label="Situação", choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    pessoa = forms.ChoiceField(label="Pessoa", choices=[('Física', 'Física'), ('Jurídica', 'Jurídica')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    cpf_cnpj = forms.CharField(label='CPF', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    ie = forms.CharField(label='Inscrição Estadual/RG', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    razao_social = forms.CharField(label='Razão Social', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    fantasia = forms.CharField(label='Fantasia', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    endereco = forms.CharField(label='Endereço', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    cep = forms.CharField(label='CEP', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    complem = forms.CharField(label='Complemento', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    bairro = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Bairro')
    cidade = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Cidade')
    uf = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Estado')
    numero = forms.CharField(label='Nº', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    tel = forms.CharField(label="Fone", max_length=20, widget=forms.TextInput(attrs={'maxlength': '20', 'class': 'form-control form-control-sm border-dark-subtle'}))
    email = forms.CharField(label='E-mail', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-lowercase'}))
    class Meta:
        model = Fornecedor
        fields = ('situacao', 'pessoa', 'cpf_cnpj', 'ie', 'razao_social', 'fantasia', 'cep', 'endereco', 'numero', 'bairro', 'complem', 'cidade', 'uf', 'tel', 'email')
    def __init__(self, *args, user=None, **kwargs):
        # Captura e remove a empresa dos kwargs de forma segura
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if not self.empresa and self.instance and self.instance.pk and self.instance.vinc_emp:
            self.empresa = self.instance.vinc_emp
        if self.empresa:
            bairros = Bairro.objects.filter(vinc_emp=self.empresa)
            cidades = Cidade.objects.filter(vinc_emp=self.empresa)
            estados = Estado.objects.filter(vinc_emp=self.empresa)
            self.fields['bairro'].choices = [('', 'Escolha uma opção')] + [(str(b.codigo), b.nome_bairro.upper()) for b in bairros]
            self.fields['cidade'].choices = [('', 'Escolha uma opção')] + [(str(c.codigo), c.nome_cidade.upper()) for c in cidades]
            self.fields['uf'].choices = [('', 'Escolha uma opção')] + [(str(e.codigo), e.nome_estado.upper()) for e in estados]
            if self.instance and self.instance.pk:
                if self.instance.bairro: self.initial['bairro'] = str(self.instance.bairro.codigo)
                if self.instance.cidade: self.initial['cidade'] = str(self.instance.cidade.codigo)
                if self.instance.uf: self.initial['uf'] = str(self.instance.uf.codigo)
        else:
            self.fields['bairro'].choices = [('', 'Escolha uma opção')]
            self.fields['cidade'].choices = [('', 'Escolha uma opção')]
            self.fields['uf'].choices = [('', 'Escolha uma opção')]
    def clean(self):
        cleaned_data = super().clean()
        campos_select2 = {'bairro': (Bairro, 'Bairro'), 'cidade': (Cidade, 'Cidade'), 'uf': (Estado, 'Estado')}
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