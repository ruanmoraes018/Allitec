from django import forms
from .models import PDV
from filiais.models import Filial

class PDVForm(forms.ModelForm):
    nome = forms.CharField(label='Nome', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    vinc_fil = forms.ModelChoiceField(label='Filial', queryset=Filial.objects.none(), widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    situacao = forms.ChoiceField(label='Situação', choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    class Meta:
        model = PDV
        fields = (
            'nome', 'vinc_fil', 'situacao'
        )
    def __init__(self, *args, empresa=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['vinc_fil'].queryset = Filial.objects.filter(vinc_emp=empresa)
            if not self.instance.pk and user and user.filial_user:
                self.fields['vinc_fil'].initial = user.filial_user.pk