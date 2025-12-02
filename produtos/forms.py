from django import forms
from .models import Produto
from unidades.models import Unidade

class ProdutoForm(forms.ModelForm):
    situacao = forms.ChoiceField(
        label='Situação',
        choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')],
        widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle'})
    )
    tp_prod = forms.ChoiceField(
        label='Tipo',
        choices=[('Principal', 'Principal'), ('Adicional', 'Adicional')],
        widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle'})
    )
    lista_orc = forms.BooleanField(
        label="Exibir na Lista (Orçamentos)",
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'role': 'switch',
        })
    )
    unidProd = forms.ModelChoiceField(
        queryset=Unidade.objects.all(),
        widget=forms.Select(
            attrs={
                'class': 'form-control form-control-sm border-dark-subtle text-uppercase',
                'id': 'id_unidProd'
            }
        ),
        label='Unidade'
    )
    desc_prod = forms.CharField(
        label="Descrição",
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle text-uppercase'
        })
    )
    vl_compra = forms.CharField(
        label='Preço de Compra',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
            'style': 'color: #DC143C; font-weight: bold; background: honeydew;',
        })
    )
    estoque_prod = forms.DecimalField(
        label='Estoque',
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
            'placeholder': '0.00'
        })
    )

    class Meta:
        model = Produto
        fields = (
            'situacao', 'tp_prod', 'desc_prod', 'grupo', 'marca',
            'unidProd', 'vl_compra', 'estoque_prod', 'lista_orc'
        )

    def __init__(self, *args, **kwargs):
        super(ProdutoForm, self).__init__(*args, **kwargs)

