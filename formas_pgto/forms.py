from django import forms
from .models import FormaPgto

class FormaPgtoForm(forms.ModelForm):
    situacao = forms.ChoiceField(label="Situação", choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    troco = forms.ChoiceField(label="Permite troco?", choices=[('Sim', 'Sim'), ('Não', 'Não')],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    tipo = forms.ChoiceField(label="Tipo", choices=[('A vista', 'A vista'), ('A prazo', 'A prazo')],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    descricao = forms.CharField(label='Descrição',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))

    class Meta:
        model = FormaPgto
        fields = (
            'situacao', 'troco', 'tipo', 'descricao'
        )