from django import forms
from django.forms import inlineformset_factory
from filiais.models import Filial
from .models import Entrada, EntradaProduto
from fornecedores.models import Fornecedor

class EntradaForm(forms.ModelForm):
    fornecedor = forms.ModelChoiceField(label='Fornecedor', queryset=Fornecedor.objects.none(), widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    vinc_fil = forms.ModelChoiceField(label='Filial', queryset=Filial.objects.none(), widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle text-uppercase'}))
    obs = forms.CharField(label='Observações', required=False, widget=forms.Textarea(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase', 'rows': 2}))
    numeracao = forms.CharField(label='Nº', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    tp_frete = forms.ChoiceField(label="Frete", choices=[('CIF', 'CIF'), ('FOB', 'FOB')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    tipo = forms.ChoiceField(choices=[('Pedido', 'Pedido'), ('Nota Fiscal', 'Nota Fiscal')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    modelo = forms.CharField(label='Modelo', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'readonly': 'readonly'}))
    serie = forms.CharField(label='Série', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'readonly': 'readonly'}))
    nat_op = forms.CharField(label='Natureza de Operação', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'readonly': 'readonly'}))
    chave_acesso = forms.CharField(label='Chave de Acesso', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'readonly': 'readonly'}))
    motivo = forms.CharField(label='Motivo', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    dt_emi = forms.DateField(label='Dt Emissão.', input_formats=['%d/%m/%Y'], widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    dt_ent = forms.DateField(label='Dt Entrega', input_formats=['%d/%m/%Y'], widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    frete = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'hidden': ''}))
    total = forms.DecimalField(label="Total", required=False, widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'readonly': 'readonly'}))

    class Meta:
        model = Entrada
        exclude = ('vinc_emp', 'situacao', 'motivo')

    def __init__(self, *args, empresa=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['fornecedor'].queryset = Fornecedor.objects.filter(vinc_emp=empresa)
            self.fields['vinc_fil'].queryset = Filial.objects.filter(vinc_emp=empresa)
            if not self.instance.pk and user and user.filial_user:
                self.fields['vinc_fil'].initial = user.filial_user.pk
        if self.instance and self.instance.pk:
            if self.instance.dt_emi:
                self.initial['dt_emi'] = self.instance.dt_emi.strftime('%d/%m/%Y')
            if self.instance.dt_ent:
                self.initial['dt_ent'] = self.instance.dt_ent.strftime('%d/%m/%Y')

    def clean_obs(self):
        return self.cleaned_data['obs'].upper()

EntradaProdutoFormSet = inlineformset_factory(
    Entrada,
    EntradaProduto,
    fields=["produto", "quantidade", "preco_unitario", "desconto"],
    extra=1,
    can_delete=True
)
