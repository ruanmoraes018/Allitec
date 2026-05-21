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
    unidProd = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Unidade')
    grupo = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Grupo')
    marca = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Marca')
    desc_prod = forms.CharField(label="Descrição", widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    vl_compra = forms.CharField(label='Preço de Compra', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-end', 'style': 'color: #DC143C; font-weight: bold; background: honeydew;'}))
    estoque_prod = forms.CharField(label='Estoque', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'placeholder': '0.00'}))
    especifico = forms.ChoiceField(label='', required=False, choices=[('', ''), ('Portinhola', 'Portinhola'), ('Alçapão', 'Alçapão'), ('Coluna Removível', 'Coluna Removível'), ('Serviço/Transporte', 'Serviço/Transporte')], widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))

    class Meta:
        model = Produto
        fields = ('situacao', 'tp_prod', 'desc_prod', 'grupo', 'marca', 'unidProd', 'vl_compra', 'estoque_prod', 'lista_orc', 'especifico')

    def __init__(self, *args, **kwargs):
        # Captura e remove a empresa dos kwargs de forma segura
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if not self.empresa and self.instance and self.instance.pk and self.instance.vinc_emp:
            self.empresa = self.instance.vinc_emp
        if self.empresa:
            unidades = Unidade.objects.filter(vinc_emp=self.empresa)
            grupos = Grupo.objects.filter(vinc_emp=self.empresa)
            marcas = Marca.objects.filter(vinc_emp=self.empresa)
            self.fields['unidProd'].choices = [('', 'Escolha uma opção')] + [(str(u.codigo), u.nome_unidade.upper()) for u in unidades]
            self.fields['grupo'].choices = [('', 'Escolha uma opção')] + [(str(g.codigo), g.nome_grupo.upper()) for g in grupos]
            self.fields['marca'].choices = [('', 'Escolha uma opção')] + [(str(m.codigo), m.nome_marca.upper()) for m in marcas]
            if self.instance and self.instance.pk:
                if self.instance.unidProd: self.initial['unidProd'] = str(self.instance.unidProd.codigo)
                if self.instance.grupo: self.initial['grupo'] = str(self.instance.grupo.codigo)
                if self.instance.marca: self.initial['marca'] = str(self.instance.marca.codigo)
                self.initial['vl_compra'] = format_decimal_br(self.instance.vl_compra)
                self.initial['estoque_prod'] = format_decimal_br(self.instance.estoque_prod)
        else:
            self.fields['unidProd'].choices = [('', 'Escolha uma opção')]
            self.fields['grupo'].choices = [('', 'Escolha uma opção')]
            self.fields['marca'].choices = [('', 'Escolha uma opção')]
    def clean(self):
        cleaned_data = super().clean()
        try: cleaned_data['vl_compra'] = parse_decimal(cleaned_data.get('vl_compra'))
        except: self.add_error('vl_compra', 'Valor inválido.')
        try: cleaned_data['estoque_prod'] = parse_decimal(cleaned_data.get('estoque_prod'))
        except: self.add_error('estoque_prod', 'Valor inválido.')
        campos_select2 = {
            'unidProd': (Unidade, 'Unidade'),
            'grupo': (Grupo, 'Grupo'),
            'marca': (Marca, 'Marca'),
        }
        for nome_campo, (model_classe, nome_exibicao) in campos_select2.items():
            codigo = cleaned_data.get(nome_campo)
            # Se o usuário preencheu o campo (não é None e nem string vazia)
            if codigo and codigo != '':
                try:
                    objeto_real = model_classe.objects.get(codigo=codigo, vinc_emp=self.empresa)
                    cleaned_data[nome_campo] = objeto_real  # Substitui pelo objeto do banco
                except model_classe.DoesNotExist:
                    self.add_error(nome_campo, f"{nome_exibicao} inválido(a) para esta empresa.")
            else:
                # ✅ CORREÇÃO: Se veio vazio ou '', força a ser None para o Django salvar como NULL
                cleaned_data[nome_campo] = None
        return cleaned_data

class ProdutoTabelaForm(forms.ModelForm):
    vl_prod = forms.DecimalField(localize=False)
    class Meta:
        model = ProdutoTabela
        fields = ('produto', 'tabela')
    localized_fields = ('vl_prod', )