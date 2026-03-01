from django import forms
from django.contrib.auth import authenticate
from .models import Filial
from bancos.models import Banco
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado
from django.contrib.auth import get_user_model
from empresas.models import Empresa
from django.db.models import Q

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
        if not all([empresa_login, username, password]):
            return cleaned_data
        try:
            empresa = Empresa.objects.filter(id=empresa_login, situacao='Ativa', contrato__situacao='Ativo').distinct().first()
            if not empresa:
                raise forms.ValidationError("Empresa não encontrada, inativa ou sem contrato ativo.")
        except Empresa.DoesNotExist:
            raise forms.ValidationError("Empresa não encontrada ou inativa.")
        user = authenticate(request=self.request if hasattr(self, 'request') else None, username=username.strip().lower(), password=password, empresa_id=empresa.id)
        if user is None:
            raise forms.ValidationError("Usuário, senha ou empresa incorretos.")
        cleaned_data["user"] = user
        cleaned_data["empresa_login"] = empresa
        return cleaned_data

class FilialForm(forms.ModelForm):
    situacao = forms.ChoiceField(label="Situação", choices=[('Ativa', 'Ativa'), ('Inativa', 'Inativa')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    cnpj = forms.CharField(label='CNPJ', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    ie = forms.CharField(label='Inscrição Estadual', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    razao_social = forms.CharField(label='Razão Social', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    fantasia = forms.CharField(label='Fantasia', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    endereco = forms.CharField(label='Endereço', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    cep = forms.CharField(label='CEP', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    bairro_fil = forms.ModelChoiceField(queryset=Bairro.objects.none(), required=False, widget=forms.Select(attrs={ 'class': 'form-control form-control-sm border-dark-subtle text-uppercase', 'id': 'id_bairro_fil'}), label='Bairro')
    complem = forms.CharField(label='Complemento', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    cidade_fil = forms.ModelChoiceField(queryset=Cidade.objects.none(), required=False, widget=forms.Select(attrs={ 'class': 'form-control form-control-sm border-dark-subtle text-uppercase', 'id': 'id_cidade_fil'}), label='Cidade')
    uf = forms.ModelChoiceField(queryset=Estado.objects.none(), required=False, widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase', 'id': 'id_uf'}), label='Estado')
    numero = forms.CharField(label='Nº', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    tel = forms.CharField(label="Fone", max_length=20, widget=forms.TextInput(attrs={'maxlength': '20', 'class': 'form-control form-control-sm border-dark-subtle'}))
    email = forms.CharField(label='E-mail', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-lowercase'}))
    tp_chave = forms.ChoiceField(label="Tipo de Chave", choices=[('', ''), ('CPF', 'CPF'), ('CNPJ', 'CNPJ'), ('E-mail', 'E-mail'), ('Telefone', 'Telefone'), ('Chave Aleatória', 'Chave Aleatória')], required=False, widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    banco_fil = forms.ModelChoiceField(queryset=Banco.objects.none(), required=False, widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Banco')
    beneficiario = forms.CharField(label='Beneficiário', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    chave_pix = forms.CharField(label='Chave Pix', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-lowercase'}))
    dt_criacao = forms.CharField(label='DT. Criação', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-lowercase', 'disabled': 'disabled'}))
    info_comp = forms.CharField(label='Informações Rodapé - Comprovantes', required=False, widget=forms.Textarea(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'rows': 2}))
    info_local = forms.CharField(label='Info. Local Atendimento - Propostas', required=False, widget=forms.Textarea(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'rows': 2}))
    info_orcamento = forms.CharField(label='Informações Rodapé - Orçamento', required=False, widget=forms.Textarea(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'rows': 2}))
    layout_contrato = forms.ChoiceField(label="Layout Contrato", choices=[('Layout 1', 'Layout 1'), ('Layout 2', 'Layout 2')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    tp_calc_juros = forms.ChoiceField(label="Tp. Cálculo Juros", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    tp_calc_multa = forms.ChoiceField(label="Tp. Cálculo Multa", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    ft_juros = forms.DecimalField(label='Fator Juros', max_digits=10, decimal_places=2, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase text-end fw-bold'}))
    ft_multa = forms.DecimalField(label='Fator Multa', max_digits=10, decimal_places=2, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase text-end fw-bold'}))
    max_parcelas = forms.DecimalField(label='Máx. Parc. (Contas R.)', max_digits=10, decimal_places=2, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase text-end fw-bold'}))

    class Meta:
        model = Filial
        fields = (
            'situacao', 'cnpj', 'ie', 'razao_social', 'fantasia', 'cep', 'endereco', 'numero', 'bairro_fil', 'cidade_fil', 'uf', 'tel', 'email', 'dt_criacao', 'logo', 'tp_chave', 'chave_pix', 'banco_fil', 'info_comp', 'complem',
            'beneficiario', 'info_orcamento', 'layout_contrato', 'info_local', 'tp_calc_juros', 'tp_calc_multa', 'ft_juros', 'ft_multa', 'max_parcelas'
        )

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            # --- BAIRRO ---
            qs_bairro_fil = Bairro.objects.filter(vinc_emp=empresa)
            if getattr(self.instance, 'bairro_fil', None):
                qs_bairro_fil = qs_bairro_fil | Bairro.objects.filter(pk=self.instance.bairro_fil.pk)
            self.fields['bairro_fil'].queryset = qs_bairro_fil.distinct()

            # --- CIDADE ---
            qs_cidade_fil = Cidade.objects.filter(vinc_emp=empresa)
            if getattr(self.instance, 'cidade_fil', None):
                qs_cidade_fil = qs_cidade_fil | Cidade.objects.filter(pk=self.instance.cidade_fil.pk)
            self.fields['cidade_fil'].queryset = qs_cidade_fil.distinct()

            # --- UF ---
            qs_uf = Estado.objects.filter(vinc_emp=empresa)
            if getattr(self.instance, 'uf', None):
                qs_uf = qs_uf | Estado.objects.filter(pk=self.instance.uf.pk)
            self.fields['uf'].queryset = qs_uf.distinct()

            # --- BAIRRO ---
            qs_banco = Banco.objects.filter(vinc_emp=empresa)
            if getattr(self.instance, 'banco_fil', None):
                qs_banco = qs_banco | Banco.objects.filter(pk=self.instance.banco_fil.pk)
            self.fields['banco_fil'].queryset = qs_banco.distinct()


class FilialReadOnlyForm(forms.ModelForm):
    class Meta:
        model = Filial
        fields = (
            'situacao', 'cnpj', 'ie', 'razao_social', 'fantasia', 'cep', 'endereco', 'numero', 'bairro_fil', 'cidade_fil', 'uf', 'tel', 'email', 'dt_criacao', 'logo', 'tp_chave', 'chave_pix', 'banco_fil', 'info_comp', 'complem',
            'beneficiario', 'info_orcamento', 'layout_contrato', 'info_local', 'tp_calc_juros', 'tp_calc_multa', 'ft_juros', 'ft_multa', 'max_parcelas'
        )

    def __init__(self, *args, empresa=None, **kwargs):
        super(FilialReadOnlyForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.disabled = True