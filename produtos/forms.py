from django import forms
from .models import Produto, ProdutoTabela
from unidades.models import Unidade
from marcas.models import Marca
from grupos.models import Grupo
from util.parse_decimal import parse_decimal, format_decimal_br
class ProdutoForm(forms.ModelForm):
    situacao = forms.ChoiceField(label='Situação', choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')], widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    tp_prod = forms.ChoiceField(label='', required=False, choices=[('Principal', 'Principal'), ('Adicional', 'Adicional')], widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    lista_orc = forms.BooleanField(label="Exibir na Lista (Orçamentos)", required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}))
    unidProd = forms.ModelChoiceField(queryset=Unidade.objects.none(), widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Unidade')
    grupo = forms.ModelChoiceField(queryset=Grupo.objects.none(), widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Grupo')
    marca = forms.ModelChoiceField(queryset=Marca.objects.none(), widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Marca')
    desc_prod = forms.CharField(label="Descrição", widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    vl_compra = forms.CharField(label='Preço de Compra', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-end', 'style': 'color: #DC143C; font-weight: bold; background: honeydew;'}))
    estoque_prod = forms.CharField(label='Estoque', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'placeholder': '0.00'}))
    especifico = forms.ChoiceField(label='', required=False, choices=[('', ''), ('Portinhola', 'Portinhola'), ('Alçapão', 'Alçapão'), ('Coluna Removível', 'Coluna Removível'), ('Serviço/Transporte', 'Serviço/Transporte')], widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))

    class Meta:
        model = Produto
        fields = ('situacao', 'tp_prod', 'desc_prod', 'grupo', 'marca', 'unidProd', 'vl_compra', 'estoque_prod', 'lista_orc', 'especifico')

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['unidProd'].queryset = Unidade.objects.filter(vinc_emp=empresa)
            self.fields['marca'].queryset = Marca.objects.filter(vinc_emp=empresa)
            self.fields['grupo'].queryset = Grupo.objects.filter(vinc_emp=empresa)
        if self.instance and self.instance.pk:
            self.initial['vl_compra'] = format_decimal_br(self.instance.vl_compra)
            self.initial['estoque_prod'] = format_decimal_br(self.instance.estoque_prod)
    def clean(self):
        cleaned_data = super().clean()
        try: cleaned_data['vl_compra'] = parse_decimal(cleaned_data.get('vl_compra'))
        except: self.add_error('vl_compra', 'Valor inválido.')
        try: cleaned_data['estoque_prod'] = parse_decimal(cleaned_data.get('estoque_prod'))
        except: self.add_error('estoque_prod', 'Valor inválido.')
        return cleaned_data
class ProdutoTabelaForm(forms.ModelForm):
    vl_prod = forms.DecimalField(localize=False)
    class Meta:
        model = ProdutoTabela
        fields = ('produto', 'tabela')
    localized_fields = ('vl_prod', )