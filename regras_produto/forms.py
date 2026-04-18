from django import forms
from .models import RegraProduto
import ast
from produtos.models import Produto

class RegraProdutoForm(forms.ModelForm):
    codigo = forms.CharField(label="Cód. Identificador", widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase', 'placeholder': 'Ex: MOTOR_PESO, LAMINA_M2'}))
    descricao = forms.CharField(label="Descrição", widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase', 'placeholder': 'Descrição da regra'}))
    ativo = forms.ChoiceField(label='Ativo', choices=[(True, 'Sim'), (False, 'Não')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    tipo_regra = forms.ChoiceField(label='Tipo Regra', required=False, choices=[('', ''), ('qtd', 'Quantidade (múltiplos produtos)'),('peso', 'Por Peso (máx)'), ('simples', 'Valor Simples')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    produto = forms.ModelChoiceField(queryset=Produto.objects.none(), required=False, widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Produto')
    class Meta:
        model = RegraProduto
        fields = ['codigo', 'descricao', 'tipo', 'produto', 'ativo', 'tipo_regra']
        widgets = {
            'tipo': forms.Select(attrs={
                'class': 'form-select form-select-sm border-dark-subtle'
            }),
        }
    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        produto = cleaned_data.get('produto')

        if tipo == 'QTD':
            # Produto agora vem via JSON
            cleaned_data['produto'] = None

        if tipo == 'SELECAO':
            cleaned_data['produto'] = None

        return cleaned_data
    
    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)

        if empresa:
            self.fields['produto'].queryset = Produto.objects.filter(vinc_emp=empresa)

class ImportarRegraProdutoForm(forms.Form):
    arquivo = forms.FileField(
        label="Planilha de Regras (.xlsx)",
        help_text="Arquivo no formato Excel",
        widget=forms.ClearableFileInput(attrs={
            'type': 'file',
            'class': 'form-control form-control-sm border-dark-subtle',
            'accept': '.xlsx'
        })
    )