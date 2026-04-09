from django import forms
from .models import RegraProduto
import ast

class RegraProdutoForm(forms.ModelForm):
    codigo = forms.CharField(label="Cód. Identificador", widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    descricao = forms.CharField(label="Descrição", widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    ativo = forms.ChoiceField(label='Ativo', choices=[(True, 'Sim'), (False, 'Não')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    tipo_regra = forms.ChoiceField(label='Tipo Regra', required=False, choices=[('', ''), ('peso', 'Por Peso (máx)'), ('simples', 'Valor Simples')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    class Meta:
        model = RegraProduto
        fields = ['codigo', 'descricao', 'tipo', 'expressao', 'ativo', 'tipo_regra']
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control form-control-sm border-dark-subtle text-uppercase',
                'placeholder': 'Ex: MOTOR_PESO, LAMINA_M2'
            }),
            'descricao': forms.TextInput(attrs={
                'class': 'form-control form-control-sm border-dark-subtle text-uppercase',
                'placeholder': 'Descrição da regra'
            }),
            'tipo': forms.Select(attrs={
                'class': 'form-select form-select-sm border-dark-subtle'
            }),
            'expressao': forms.Textarea(attrs={
                'class': 'form-control form-control-sm border-dark-subtle',
                'rows': 6,
                'placeholder': 'Ex: (alt_c + 0.2) * 2'
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    def clean_expressao(self):
        expr = self.cleaned_data['expressao']
        tipo = self.cleaned_data.get('tipo')
        VARIAVEIS_PERMITIDAS = {
            'larg', 'larg_c', 'alt', 'alt_c', 'm2', 'peso', 'ft_peso', 'qtd_lam', 'eix_mot', 'rolo'
        }
        if tipo == 'QTD':
            try:
                tree = ast.parse(expr, mode='eval')
            except SyntaxError:
                raise forms.ValidationError("Expressão inválida.")
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    if node.id not in VARIAVEIS_PERMITIDAS:
                        raise forms.ValidationError(
                            f"Variável '{node.id}' não é permitida."
                        )
                elif not isinstance(
                    node,
                    (ast.Expression, ast.BinOp, ast.UnaryOp,
                     ast.Num, ast.Load, ast.Add, ast.Sub,
                     ast.Mult, ast.Div, ast.Pow, ast.Mod,
                     ast.Constant, ast.Call)
                ):
                    raise forms.ValidationError("Operação não permitida.")
        return expr

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