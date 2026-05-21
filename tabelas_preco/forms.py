from django import forms
from .models import TabelaPreco
from util.parse_decimal import parse_decimal

class TabelaPrecoForm(forms.ModelForm):
    descricao = forms.CharField(label='Descrição', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    margem = forms.CharField(label="Margem (%)", widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    tipo = forms.ChoiceField(label='Tipo de Plano', choices=[('A prazo', 'A prazo'), ('A vista', 'A vista')], widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    class Meta:
        model = TabelaPreco
        fields = ('descricao', 'margem', 'tipo')
    def clean(self):
        cleaned_data = super().clean()
        try: cleaned_data['margem'] = parse_decimal(cleaned_data.get('margem'))
        except: self.add_error('margem', 'Valor inválido.')
        return cleaned_data