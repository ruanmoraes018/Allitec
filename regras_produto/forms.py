from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column
from .models import (RegraProduto, GrupoRegraProduto, RegraProdutoItem, CondicaoRegraProduto,)
from produtos.models import Produto
import json
from django.forms import inlineformset_factory


CATEGORIA_CHOICES = [("lamina", "Lâmina"), ("motor", "Motor"), ("eixo", "Eixo"), ("mola", "Mola"), ("pintura", "Pintura"),("testeira",  "Testeira"), ("acessorio", "Acessório"), ("outro", "Outro"),]
c = 'form-control form-control-sm border-dark-subtle focus-ring focus-ring-dark'
s = 'form-select form-select-sm border-dark-subtle focus-ring focus-ring-dark'

class RegraProdutoForm(forms.ModelForm):
    codigo = forms.CharField(label="Código", widget=forms.TextInput(attrs={"class":f"{c} text-uppercase", "placeholder":"Ex: MOTOR_PESO"}))
    descricao = forms.CharField(label="Descrição", widget=forms.TextInput(attrs={"class":f"{c} text-uppercase"}))
    categoria = forms.ChoiceField(choices=CATEGORIA_CHOICES, widget=forms.Select(attrs={"class":f"{s}"}))
    formula = forms.CharField(label="Fórmula", widget=forms.Textarea(attrs={"class":f"{c}","rows":2, "placeholder":"JSON opcional"}))
    ativo = forms.ChoiceField(label='Ativo', choices=[(True, 'Sim'), (False, 'Não')], widget=forms.Select(attrs={"class":f"{s}"}))

    class Meta:
        model = RegraProduto
        exclude = ("vinc_emp", "cod_local", "criado_em", "alterado_em",)
        widgets = {
            "grupo": forms.Select(attrs={"class":"form-select form-select-sm", "id":"id_grupo_regra"}),
            "tipo": forms.Select(attrs={"class":"form-select form-select-sm"}),
            "ordem": forms.NumberInput(attrs={"class":"form-control form-control-sm", "min":0}),
        }

    def __init__(self,*args,empresa=None,**kwargs):
        super().__init__(*args,**kwargs)
        if empresa:
            self.fields["grupo"].queryset = (GrupoRegraProduto.objects.filter(vinc_emp=empresa))
        self.helper = FormHelper()
        self.helper.form_tag=False
        self.helper.layout = Layout(
            Row(Column("grupo",css_class="col-md-4"),Column("categoria",css_class="col-md-3"),Column("tipo",css_class="col-md-3"),Column("ativo",css_class="col-md-2"),),
            Row(Column("codigo", css_class="col-md-4"), Column("descricao", css_class="col-md-6"), Column("ordem", css_class="col-md-2"),),
            Row(Column("formula", css_class="col-md-12"))
        )

class RegraProdutoItemForm(forms.ModelForm):
    # Define o campo produto com to_field_name="codigo"
    produto = forms.ModelChoiceField(
        queryset=Produto.objects.none(),
        to_field_name="codigo",
        widget=forms.Select(attrs={"class": "produto-select form-select form-select-sm"})
    )
    
    condicoes_json = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

    class Meta:
        model = RegraProdutoItem
        fields = ("produto", "formula_qtd", "descricao", "prioridade")
        widgets = {
            "formula_qtd": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Ex: ceil(area/0.8)"}),
            "descricao": forms.TextInput(attrs={"class": "form-control form-control-sm border-dark-subtle"}),
            "prioridade": forms.NumberInput(attrs={"class": "form-control form-control-sm", "min": 0}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa

        if self.empresa:
            # Garante a isolação multiempresa: limita a validação apenas aos produtos da empresa logada
            self.fields["produto"].queryset = Produto.objects.filter(vinc_emp=self.empresa)

        # Trata as opções exibidas no HTML/Select sem quebrar a validação
        codigo_enviado = self.data.get(self.add_prefix('produto')) if self.data else None

        if codigo_enviado:
            prod = Produto.objects.filter(codigo=codigo_enviado, vinc_emp=self.empresa).first()
            if prod:
                self.fields["produto"].choices = [(prod.codigo, f"{prod.codigo} - {prod.desc_prod}")]
        elif self.instance and self.instance.pk and self.instance.produto_id:
            p = self.instance.produto
            self.fields["produto"].choices = [(p.codigo, f"{p.codigo} - {p.desc_prod}")]
            
            # Pré-popula condições do JSON
            condicoes = list(self.instance.condicoes.values('campo', 'operador', 'valor', 'ordem'))
            if condicoes:
                self.fields["condicoes_json"].initial = json.dumps(condicoes)

    def clean_produto(self):
        # Como o ModelChoiceField (com to_field_name) já valida e retorna o objeto Produto correto da empresa,
        # basta pegar o valor já validado.
        produto = self.cleaned_data.get("produto")
        if not produto:
            raise forms.ValidationError("Produto é obrigatório.")
        return produto


# Mantém apenas o ItemFormSet
ItemFormSet = inlineformset_factory(
    RegraProduto, RegraProdutoItem,
    form=RegraProdutoItemForm,
    extra=1, can_delete=True
)

class ImportarRegraProdutoForm(forms.Form):
    arquivo = forms.FileField(label="Planilha de Regras (.xlsx)", widget=forms.ClearableFileInput(attrs={"class":"form-control form-control-sm","accept":".xlsx"}))

class GrupoRegraProdutoForm(forms.ModelForm):
    ativo = forms.ChoiceField(label='Ativo', choices=[(True, 'Sim'), (False, 'Não')], widget=forms.Select(attrs={"class":f"{s}"}))
    codigo = forms.CharField(label="Código", widget=forms.TextInput(attrs={"class":f"{c} text-uppercase"}))
    descricao = forms.CharField(label="Descrição", widget=forms.TextInput(attrs={"class":f"{c} text-uppercase"}))
    ordem = forms.CharField(label="Ordem", widget=forms.NumberInput(attrs={"class":f"{c}"}))

    class Meta:
        model = GrupoRegraProduto
        fields = ("ativo","codigo","descricao","ordem")
        widgets = {
            "codigo": forms.TextInput(attrs={"class":"form-control form-control-sm border-dark-subtle focus-ring focus-ring-dark"}),
            "descricao": forms.TextInput(attrs={"class":"form-control form-control-sm border-dark-subtle focus-ring focus-ring-dark"}),
            "ativo": forms.Select(attrs={"class": "form-control form-control-sm border-dark-subtle focus-ring focus-ring-dark"}),
            "ordem": forms.NumberInput(attrs={"class":"form-control form-control-sm"})
        }
