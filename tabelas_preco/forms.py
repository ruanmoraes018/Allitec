from django import forms
from .models import TabelaPreco

class TabelaPrecoForm(forms.ModelForm):
    descricao = forms.CharField(label='Descrição', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    margem = forms.DecimalField(label="Margem (%)", widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    tipo = forms.ChoiceField(label='Tipo de Plano', choices=[('A prazo', 'A prazo'), ('A vista', 'A vista')], widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    class Meta:
        model = TabelaPreco
        fields = ('descricao', 'margem', 'tipo')