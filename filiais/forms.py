from django import forms
from django.contrib.auth import authenticate
from .models import Filial
from bancos.models import Banco
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado
from django.contrib.auth import get_user_model
from empresas.models import Empresa

Usuario = get_user_model()

class EmpresaLoginForm(forms.Form):
    empresa = forms.IntegerField(
        label="ID da Empresa",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    username = forms.CharField(
        label="Usuário",
        widget=forms.TextInput(attrs={'class': 'form-control text-lowercase'})
    )
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput
    )

    def clean(self):
        cleaned_data = super().clean()
        empresa = cleaned_data.get("empresa")
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")

        if not all([empresa, username, password]):
            return cleaned_data

        # Verifica se a empresa existe e está ativa
        try:
            empresa = Empresa.objects.get(id=empresa, situacao='Ativa')
        except Empresa.DoesNotExist:
            raise forms.ValidationError("Empresa não encontrada ou inativa.")

        # Autenticação usando backend customizado
        # cleaned_data
        user = authenticate(
            request=self.request if hasattr(self, 'request') else None,
            username=username.strip().lower(),
            password=password,
            empresa_id=empresa.id
        )


        if user is None:
            raise forms.ValidationError("Usuário, senha ou empresa incorretos.")

        cleaned_data["user"] = user
        cleaned_data["empresa"] = empresa
        return cleaned_data


class FilialForm(forms.ModelForm):
    situacao = forms.ChoiceField(label="Situação", choices=[('Ativa', 'Ativa'), ('Inativa', 'Inativa')],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    cnpj = forms.CharField(label='CNPJ',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    ie = forms.CharField(label='Inscrição Estadual', required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    razao_social = forms.CharField(label='Razão Social',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    fantasia = forms.CharField(label='Fantasia',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    endereco = forms.CharField(label='Endereço',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    cep = forms.CharField(label='CEP',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    bairro_fil = forms.ModelChoiceField(
        queryset=Bairro.objects.all(),
        required=False,
        widget=forms.Select(
            attrs={
                'class': 'form-control form-control-sm border-dark-subtle text-uppercase',
                'id': 'id_bairro_fil'
            }
        ),
        label='Bairro'
    )
    complem = forms.CharField(label='Complemento', required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    cidade_fil = forms.ModelChoiceField(
        queryset=Cidade.objects.all(),
        required=False,
        widget=forms.Select(
            attrs={
                'class': 'form-control form-control-sm border-dark-subtle text-uppercase',
                'id': 'id_cidade_fil'
            }
        ),
        label='Cidade'
    )
    uf = forms.ModelChoiceField(
        queryset=Estado.objects.all(),
        required=False,
        widget=forms.Select(
            attrs={
                'class': 'form-control form-control-sm border-dark-subtle text-uppercase',
                'id': 'id_uf'
            }
        ),
        label='Estado'
    )
    numero = forms.CharField(label='Nº',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    tel = forms.CharField(label="Fone", max_length=20, widget=forms.TextInput(attrs={'maxlength': '20', 'class': 'form-control form-control-sm border-dark-subtle'}))
    email = forms.CharField(label='E-mail',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-lowercase'}))
    tp_chave = forms.ChoiceField(label="Tipo de Chave", choices=[('', ''), ('CPF', 'CPF'), ('CNPJ', 'CNPJ'), ('E-mail', 'E-mail'), ('Telefone', 'Telefone'), ('Chave Aleatória', 'Chave Aleatória')], required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    banco_fil = forms.ModelChoiceField(
        queryset=Banco.objects.all(),
        required=False,
        widget=forms.Select(
            attrs={
                'class': 'form-control form-control-sm border-dark-subtle text-uppercase',
                'id': 'id_banco_fil'
            }
        ),
        label='Banco'
    )
    beneficiario = forms.CharField(label='Beneficiário', required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))

    chave_pix = forms.CharField(label='Chave Pix', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-lowercase'}))
    dt_criacao = forms.CharField(label='DT. Criação', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-lowercase', 'disabled': 'disabled'}))

    info_comp = forms.CharField(
        label='Informações Rodapé - Comprovantes',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
            'rows': 2
        })
    )

    info_orcamento = forms.CharField(
        label='Informações Rodapé - Orçamento',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
            'rows': 2
        })
    )
    layout_contrato = forms.ChoiceField(label="Layout Contrato", choices=[('Layout 1', 'Layout 1'), ('Layout 2', 'Layout 2')],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))

    class Meta:
        model = Filial
        fields = (
            'situacao', 'cnpj', 'ie', 'razao_social', 'fantasia', 'cep', 'endereco', 'numero', 'bairro_fil', 'cidade_fil', 'uf', 'tel', 'email', 'dt_criacao', 'logo', 'tp_chave', 'chave_pix', 'banco_fil', 'info_comp', 'complem',
            'beneficiario', 'info_orcamento', 'layout_contrato'
        )

class FilialReadOnlyForm(forms.ModelForm):
    class Meta:
        model = Filial
        fields = (
            'situacao', 'cnpj', 'ie', 'razao_social', 'fantasia', 'cep', 'endereco', 'numero', 'bairro_fil', 'cidade_fil', 'uf', 'tel', 'email', 'dt_criacao', 'logo', 'tp_chave', 'chave_pix', 'banco_fil', 'info_comp', 'complem',
            'beneficiario'
        )

    def __init__(self, *args, **kwargs):
        super(FilialReadOnlyForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.disabled = True