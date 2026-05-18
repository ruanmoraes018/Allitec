from django import forms
from .models import Caixa
from filiais.models import Filial
from pdvs.models import PDV
from formas_pgto.models import FormaPgto

class CaixaForm(forms.ModelForm):
    terminal = forms.ModelChoiceField(label='PDV', queryset=PDV.objects.none(), widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    observacao = forms.CharField(label='Observação', required=False, widget=forms.Textarea(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'rows': 1}))
    class Meta:
        model = Caixa
        fields = ('observacao', 'terminal')
    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['terminal'].queryset = PDV.objects.filter(vinc_emp=empresa)
            formas = FormaPgto.objects.filter(vinc_emp=empresa)
            for forma in formas:
                self.fields[f'forma_{forma.id}'] = forms.DecimalField(label=forma.descricao, required=False, initial=0, widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}))