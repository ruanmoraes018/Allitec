from django import forms
from util.parse_decimal import parse_decimal
from .models import ContaPagar
from filiais.models import Filial
from fornecedores.models import Fornecedor

class ContaPagarForm(forms.ModelForm):
    num_conta = forms.CharField(label='Nº Conta', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    filial = forms.ModelChoiceField(queryset=Filial.objects.none(), widget=forms.Select(attrs={ 'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Filial')
    fornecedor = forms.ModelChoiceField(queryset=Fornecedor.objects.none(), widget=forms.Select(attrs={ 'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Fornecedor')
    data_vencimento = forms.DateField(label='Dt. Vencimento', input_formats=['%d/%m/%Y'], widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    valor = forms.CharField(label='Vl. Conta', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase text-end', 'placeholder': '0,00', 'style': 'background-color: #2E8B57; color: white; font-weight: bold;'}))
    tp_juros = forms.ChoiceField(label="Tp. Juros", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    tp_multa = forms.ChoiceField(label="Tp. Multa", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    multa = forms.CharField(label='Vl. Multa', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase text-end fw-bold'}))
    juros = forms.CharField(label='Vl. Juros', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase text-end fw-bold'}))
    observacao = forms.CharField(label='Observações', required=False, widget=forms.Textarea(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase', 'rows': 2}))
    class Meta:
        model = ContaPagar
        exclude = ('tipo', 'empresa', 'situacao', 'valor_pago', 'orcamento', 'pedido', 'desconto', 'data_emissao', 'motivo')
        widgets = {'data_vencimento': forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle',}),}
    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['filial'].queryset = Filial.objects.filter(vinc_emp=empresa)
            self.fields['fornecedor'].queryset = Fornecedor.objects.filter(vinc_emp=empresa)
        if self.instance and self.instance.pk:
            if self.instance.data_vencimento: self.initial['data_vencimento'] = self.instance.data_vencimento.strftime('%d/%m/%Y')
    def clean(self):
        cleaned_data = super().clean()
        try: cleaned_data['valor'] = parse_decimal(cleaned_data.get('valor'))
        except: self.add_error('valor', 'Valor inválido.')
        try: cleaned_data['multa'] = parse_decimal(cleaned_data.get('multa'))
        except: self.add_error('multa', 'Valor inválido.')
        try: cleaned_data['juros'] = parse_decimal(cleaned_data.get('juros'))
        except: self.add_error('juros', 'Valor inválido.')
        return cleaned_data