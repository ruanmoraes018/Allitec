from django import forms

from util.parse_decimal import parse_decimal
from .models import Contrato
from empresas.models import Empresa

class ContratoForm(forms.ModelForm):
    empresa = forms.ModelChoiceField(
        queryset=Empresa.objects.all(),
        widget=forms.Select(
            attrs={
                'class': 'form-control form-control-sm border-dark-subtle text-uppercase',
                'id': 'id_empresa'
            }
        ),
        label='Empresa'
    )
    dt_inicio = forms.DateField(
        label='Dt. Início',
        input_formats=['%d/%m/%Y'],
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
        })
    )
    situacao = forms.ChoiceField(label="Situação", choices=[('Ativo', 'Ativo'), ('Suspenso', 'Suspenso'), ('Cancelado', 'Cancelado')],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    qtd_meses = forms.CharField(label='Qtd. Meses',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase', 'type': 'number'}))
    valor_mensalidade = forms.CharField(
        label='Vl. Parcela', # Defina conforme o modelo
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle text-uppercase',
            'placeholder': '0,00', 'style': 'background-color: #2E8B57; color: white; font-weight: bold;'
        })
    )
    obs = forms.CharField(
        label='Observações',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control form-control-sm border-dark-subtle text-uppercase',
            'rows': 2
        })
    )

    class Meta:
        model = Contrato
        exclude = ('created_at', 'updated_at', 'status')
    
    def clean(self):
        cleaned_data = super().clean()
        try:
            cleaned_data['valor_mensalidade'] = parse_decimal(
                cleaned_data.get('valor_mensalidade')
            )
        except:
            self.add_error('valor_mensalidade', 'Valor inválido.')
        return cleaned_data