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
    codigo = forms.CharField(
        label="Código",
        widget=forms.TextInput(
            attrs={
                "class": f"{c} text-uppercase",
                "placeholder": "Ex: MOTOR_PESO",
            }
        ),
    )

    descricao = forms.CharField(
        label="Descrição",
        widget=forms.TextInput(
            attrs={
                "class": f"{c} text-uppercase",
            }
        ),
    )

    categoria = forms.ChoiceField(
        choices=CATEGORIA_CHOICES,
        widget=forms.Select(
            attrs={
                "class": f"{s}",
            }
        ),
    )

    formula = forms.CharField(
        label="Fórmula",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": f"{c}",
                "rows": 2,
                "placeholder": "JSON opcional",
            }
        ),
    )

    ativo = forms.ChoiceField(
        label="Ativo",
        choices=[
            (True, "Sim"),
            (False, "Não"),
        ],
        widget=forms.Select(
            attrs={
                "class": f"{s}",
            }
        ),
    )

    # ---------------------------------------------------------
    # IMPORTANTE:
    # O valor enviado pelo HTML será o cod_local,
    # mas o cleaned_data["grupo"] será um objeto
    # GrupoRegraProduto.
    # ---------------------------------------------------------
    grupo = forms.ModelChoiceField(
        queryset=GrupoRegraProduto.objects.none(),
        to_field_name="cod_local",
        empty_label="Escolha uma opção",
        widget=forms.Select(
            attrs={
                "class": "form-select form-select-sm",
                "id": "id_grupo_regra",
            }
        ),
        required=False,
    )

    class Meta:
        model = RegraProduto

        exclude = (
            "vinc_emp",
            "cod_local",
            "criado_em",
            "alterado_em",
        )

        widgets = {
            "tipo": forms.Select(
                attrs={
                    "class": "form-select form-select-sm",
                }
            ),
            "ordem": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "min": 0,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop("empresa", None)
        self.user = kwargs.pop("user", None)

        super().__init__(*args, **kwargs)

        # ---------------------------------------------------------
        # Se não recebeu empresa explicitamente e está editando,
        # tenta obter a empresa do próprio registro.
        # ---------------------------------------------------------
        if not self.empresa:
            if self.instance and self.instance.pk:
                self.empresa = getattr(
                    self.instance,
                    "vinc_emp",
                    None
                )

        # ---------------------------------------------------------
        # Grupos disponíveis SOMENTE para a empresa atual
        # ---------------------------------------------------------
        if self.empresa:
            self.fields["grupo"].queryset = (
                GrupoRegraProduto.objects
                .filter(
                    vinc_emp=self.empresa,
                    ativo=True,
                )
                .order_by("ordem", "codigo")
            )

        # ---------------------------------------------------------
        # Valor inicial na edição
        # Como to_field_name="cod_local", basta usar o cod_local.
        # ---------------------------------------------------------
        if (
            self.instance
            and self.instance.pk
            and self.instance.grupo_id
        ):
            self.initial["grupo"] = self.instance.grupo.cod_local

        # ---------------------------------------------------------
        # Crispy Forms
        # ---------------------------------------------------------
        self.helper = FormHelper()
        self.helper.form_tag = False

        self.helper.layout = Layout(
            Row(
                Column(
                    "grupo",
                    css_class="col-md-4"
                ),
                Column(
                    "categoria",
                    css_class="col-md-3"
                ),
                Column(
                    "tipo",
                    css_class="col-md-3"
                ),
                Column(
                    "ativo",
                    css_class="col-md-2"
                ),
            ),
            Row(
                Column(
                    "codigo",
                    css_class="col-md-4"
                ),
                Column(
                    "descricao",
                    css_class="col-md-6"
                ),
                Column(
                    "ordem",
                    css_class="col-md-2"
                ),
            ),
            Row(
                Column(
                    "formula",
                    css_class="col-md-12"
                )
            ),
        )

    def clean(self):
        cleaned_data = super().clean()

        # ---------------------------------------------------------
        # Empresa obrigatória
        # ---------------------------------------------------------
        if not self.empresa:
            raise forms.ValidationError(
                "Empresa não identificada para esta operação."
            )

        # ---------------------------------------------------------
        # GRUPO
        #
        # Aqui cleaned_data["grupo"] JÁ É um GrupoRegraProduto.
        #
        # Não faça mais:
        #
        # GrupoRegraProduto.objects.get(
        #     cod_local=grupo_codigo
        # )
        # ---------------------------------------------------------
        grupo = cleaned_data.get("grupo")

        if grupo:
            # Segurança adicional:
            # garante que o grupo pertence à empresa atual.
            if grupo.vinc_emp_id != self.empresa.pk:
                self.add_error(
                    "grupo",
                    "Grupo inválido para esta empresa."
                )
            else:
                cleaned_data["grupo"] = grupo

        # ---------------------------------------------------------
        # Código único por empresa
        # ---------------------------------------------------------
        codigo = cleaned_data.get("codigo")

        if codigo:
            codigo = codigo.strip().upper()
            cleaned_data["codigo"] = codigo

            qs = RegraProduto.objects.filter(
                vinc_emp=self.empresa,
                codigo=codigo,
            )

            # Na edição, ignora o próprio registro
            if self.instance and self.instance.pk:
                qs = qs.exclude(
                    pk=self.instance.pk
                )

            if qs.exists():
                self.add_error(
                    "codigo",
                    "Já existe uma regra com este código nesta empresa."
                )

        return cleaned_data

    def save(self, commit=True):
        obj = super().save(commit=False)

        # ---------------------------------------------------------
        # A empresa NÃO vem do formulário.
        # Vem do contexto da view.
        # ---------------------------------------------------------
        obj.vinc_emp = self.empresa

        if commit:
            obj.save()
            self.save_m2m()

        return obj

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

        self.fields["produto"] = forms.ChoiceField(
            choices=[('', 'Escolha uma opção')],
            widget=forms.Select(attrs={"class": "produto-select form-select form-select-sm"}),
            required=True
        )

        codigo_enviado = self.data.get(self.add_prefix('produto')) if self.data else None

        if codigo_enviado and self.empresa:
            prod = Produto.objects.filter(codigo=codigo_enviado, vinc_emp=self.empresa).first()
            if prod:
                self.fields["produto"].choices = [
                    ('', 'Escolha uma opção'),
                    (str(prod.codigo), f"{prod.codigo} - {prod.desc_prod}")
                ]
                self.initial['produto'] = str(prod.codigo)

        elif self.instance and self.instance.pk and self.instance.produto_id:
            try:
                p = Produto.objects.get(pk=self.instance.produto_id)
                self.fields["produto"].choices = [
                    ('', 'Escolha uma opção'),
                    (str(p.codigo), f"{p.codigo} - {p.desc_prod}")
                ]
                self.initial['produto'] = str(p.codigo)
            except Produto.DoesNotExist:
                pass

            condicoes = list(self.instance.condicoes.values('campo', 'operador', 'valor', 'ordem'))
            if condicoes:
                self.fields["condicoes_json"].initial = json.dumps(condicoes)

    def clean_produto(self):
        codigo = self.cleaned_data.get("produto")
        if not codigo:
            raise forms.ValidationError("Produto é obrigatório.")
        prod = Produto.objects.filter(codigo=codigo, vinc_emp=self.empresa).first()
        if not prod:
            raise forms.ValidationError("Produto inválido.")
        return prod


# Mantém apenas o ItemFormSet
ItemFormSet = inlineformset_factory(
    RegraProduto, RegraProdutoItem,
    form=RegraProdutoItemForm,
    extra=0, can_delete=True
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
