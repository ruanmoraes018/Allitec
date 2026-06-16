from django import forms
from .models import Tecnico
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado

class TecnicoForm(forms.ModelForm):
    situacao = forms.ChoiceField(label="Situação", choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    nome = forms.CharField(label='Nome', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    endereco = forms.CharField(label='Endereço', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    cep = forms.CharField(label='CEP', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    bairro = forms.ChoiceField(required=False, widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Bairro')
    cidade = forms.ChoiceField(required=False, widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Cidade')
    uf = forms.ChoiceField(required=False, widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Estado')
    numero = forms.CharField(label='Nº', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    tel = forms.CharField(label="Fone", max_length=20, widget=forms.TextInput(attrs={'maxlength': '20', 'class': 'form-control form-control-sm border-dark-subtle'}))
    email = forms.CharField(label='E-mail', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-lowercase'}))
    class Meta:
        model = Tecnico
        fields = ('situacao', 'nome', 'cep', 'endereco', 'numero', 'bairro', 'cidade', 'uf', 'tel', 'email')
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if not self.empresa and self.instance and self.instance.pk and getattr(self.instance, 'vinc_emp', None):
            self.empresa = self.instance.vinc_emp
        if self.empresa:
            bairros = Bairro.objects.filter(vinc_emp=self.empresa)
            cidades = Cidade.objects.filter(vinc_emp=self.empresa)
            estados = Estado.objects.filter(vinc_emp=self.empresa)
            self.fields['bairro'].choices = [('', 'Escolha um Bairro')] + [(str(b.codigo), b.nome_bairro.upper()) for b in bairros]
            self.fields['cidade'].choices = [('', 'Escolha uma Cidade')] + [(str(c.codigo), c.nome_cidade.upper()) for c in cidades]
            self.fields['uf'].choices = [('', 'Escolha um Estado')] + [(str(e.codigo), e.nome_estado.upper()) for e in estados]
            # Define os valores iniciais em caso de Edição (Uso do código)
            if self.instance and self.instance.pk:
                if self.instance.bairro: self.initial['bairro'] = str(self.instance.bairro.codigo)
                if self.instance.cidade: self.initial['cidade'] = str(self.instance.cidade.codigo)
                if self.instance.uf: self.initial['uf'] = str(self.instance.uf.codigo)
        else:
            self.fields['bairro'].choices = [('', 'Escolha um Bairro')]
            self.fields['cidade'].choices = [('', 'Escolha uma Cidade')]
            self.fields['uf'].choices = [('', 'Escolha um Estado')]
    def clean(self):
        cleaned_data = super().clean()
        # Mapeamento genérico: 'nome_no_form': (ClasseDoModel, 'Nome Amigável para o Erro')
        campos_select2 = {'bairro': (Bairro, 'Bairro'), 'cidade': (Cidade, 'Cidade'), 'uf': (Estado, 'UF'),}
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