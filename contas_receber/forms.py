from django import forms
from .models import ContaReceber
from filiais.models import Filial
from clientes.models import Cliente

class ContaReceberForm(forms.ModelForm):
    num_conta = forms.CharField(label='Nº Conta', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    vinc_fil = forms.ModelChoiceField(queryset=Filial.objects.none(), widget=forms.Select(attrs={ 'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Filial')
    cliente = forms.ModelChoiceField(queryset=Cliente.objects.none(), widget=forms.Select(attrs={ 'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Cliente')
    data_vencimento = forms.DateField(label='Dt. Vencimento', input_formats=['%d/%m/%Y'], widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    valor = forms.DecimalField(label='Vl. Conta', max_digits=10, decimal_places=2, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase text-end', 'placeholder': '0,00', 'style': 'background-color: #2E8B57; color: white; font-weight: bold;'}))
    tp_juros = forms.ChoiceField(label="Tp. Juros", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    tp_multa = forms.ChoiceField(label="Tp. Multa", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    multa = forms.DecimalField(label='Vl. Multa', max_digits=10, decimal_places=2, required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase text-end fw-bold'}))
    juros = forms.DecimalField(label='Vl. Juros', max_digits=10, decimal_places=2, required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase text-end fw-bold'}))
    observacao = forms.CharField(label='Observações', required=False, widget=forms.Textarea(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase', 'rows': 2}))
    class Meta:
        model = ContaReceber
        exclude = ('vinc_emp', 'situacao', 'valor_pago', 'orcamento', 'pedido', 'forma_pgto', 'desconto', 'data_emissao')
        widgets = {
            'data_vencimento': forms.TextInput(attrs={
                'class': 'form-control form-control-sm border-dark-subtle',
            }),
        }
    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['vinc_fil'].queryset = Filial.objects.filter(vinc_emp=empresa)
            self.fields['cliente'].queryset = Cliente.objects.filter(vinc_emp=empresa)

        if self.instance and self.instance.pk:
            if self.instance.data_vencimento:
                self.initial['data_vencimento'] = self.instance.data_vencimento.strftime('%d/%m/%Y')
