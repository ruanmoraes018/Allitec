from django import forms
from .models import Cliente
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado
from filiais.models import Filial

class ClienteForm(forms.ModelForm):
    vinc_fil = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Filial')
    situacao = forms.ChoiceField(label="Situação", choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    somente_avista = forms.ChoiceField(label="Vender somente à vista", choices=[(True, 'Sim'), (False, 'Não')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
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
        model = Cliente
        fields = (
            'somente_avista', 'situacao', 'pessoa', 'cpf_cnpj', 'ie', 'razao_social', 'fantasia', 'cep', 'endereco', 'numero', 'bairro', 'complem', 'cidade', 'uf', 'tel', 'email', 'vinc_fil'
        )
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
            else:
                # ✅ Se for CRIAÇÃO (Novo Registro): Pré-seleciona a filial do usuário logado
                if self.user and self.user.filial_user:
                    self.initial['vinc_fil'] = str(self.user.filial_user.codigo)
        else:
            self.fields['bairro'].choices = [('', 'Escolha um Bairro')]
            self.fields['cidade'].choices = [('', 'Escolha uma Cidade')]
            self.fields['uf'].choices = [('', 'Escolha um Estado')]
            self.fields['vinc_fil'].choices = [('', 'Escolha uma Filial')]

    def clean(self):
        cleaned_data = super().clean()
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