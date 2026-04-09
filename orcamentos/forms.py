from django import forms
from .models import Orcamento, PortaAdicional, PortaOrcamento, PortaProduto
from clientes.models import Cliente
from tecnicos.models import Tecnico
from formas_pgto.models import FormaPgto
from filiais.models import Filial
from tabelas_preco.models import TabelaPreco
from django.db import models
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field

class OrcamentoForm(forms.ModelForm):
    cli = forms.ModelChoiceField(label='Cliente', queryset=Cliente.objects.none(), widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    vinc_fil = forms.ModelChoiceField(label='Filial', queryset=Filial.objects.none(), widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    obs_cli = forms.CharField(label='Obs', required=False, widget=forms.Textarea(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase', 'rows': 2}))
    num_orcamento = forms.CharField(label='Nº', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'disabled': 'disabled'}))
    solicitante = forms.ModelChoiceField(label='Técnico/Solicitante', queryset=Tecnico.objects.none(), widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    pintura = forms.ChoiceField(choices=[('Sim', 'Sim'),('Não', 'Não')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    portao_social = forms.ChoiceField(label="Portão Social", choices=[('Não', 'Não'),('Sim', 'Sim')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    tp_pintura = forms.ChoiceField(label="Tipo Pintura", choices=[('Eletrostática', 'Eletrostática'),('Automotiva', 'Automotiva')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    cor = forms.ChoiceField(
        choices = [
            ('', ''), ('Preto', 'Preto'), ('Branco', 'Branco'),('Amarelo', 'Amarelo'), ('Vermelho', 'Vermelho'),('Azul Claro', 'Azul Claro'), ('Cinza Claro', 'Cinza Claro'),
            ('Cinza Grafite', 'Cinza Grafite'), ('Cinza Chumbo', 'Cinza Chumbo'), ('Chumbo', 'Chumbo'), ('Verde', 'Verde'),('Bege', 'Bege'), ('Bege Areia', 'Bege Areia'),('Marrom', 'Marrom'), ('Marrom Café', 'Marrom Café'),
            ('Laranja', 'Laranja'), ('Azul Royal', 'Azul Royal'), ('Azul Marinho', 'Azul Marinho'), ('Azul Pepsi', 'Azul Pepsi'), ('Verde Musgo', 'Verde Musgo'),('Verde Bandeira', 'Verde Bandeira'), ('Vinho', 'Vinho'), ('Prata', 'Prata'),
        ],
        required=False, widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'})
    )
    obs_form_pgto = forms.CharField(label='Observações', required=False, widget=forms.Textarea(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase', 'rows': 2}))
    vl_p_s = forms.DecimalField(required=False, label="Vl. P. Social", max_digits=10, decimal_places=2,
        widget=forms.TextInput(attrs={"type": "number", "step":"0.01", "min": "0", 'placeholder': '0.00', 'disabled': 'disabled', 'class': 'form-control border-dark-subtle', 'style': 'color: darkgreen; font-weight: bold; background: honeydew;'})
    )
    desconto = forms.DecimalField(required=False, max_digits=10, decimal_places=2, widget=forms.TextInput(attrs={'class': 'form-control border-dark-subtle', 'style': 'color: #2E8B57; font-weight: bold; background-color: #808080;', 'placeholder': '0.00', 'readonly': 'readonly'}))
    acrescimo = forms.DecimalField(required=False,max_digits=10,decimal_places=2,widget=forms.TextInput(attrs={'class': 'form-control border-dark-subtle','style': 'color: #2E8B57; font-weight: bold; background-color: #808080;','placeholder': '0.00','readonly': 'readonly'}))
    dt_emi = forms.DateField(label='Dt. Emissão',input_formats=['%d/%m/%Y'],widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    dt_ent = forms.DateField(label='Dt. Entrega',required=False,input_formats=['%d/%m/%Y'],widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    subtotal = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle','hidden': ''}))
    total = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle','hidden': ''}))
    formas_pgto = forms.ModelChoiceField(label='Formas de Pagamento', required=False, queryset=FormaPgto.objects.none(), widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    tabela_preco = forms.ModelChoiceField(label='Tabela de Preço', queryset=TabelaPreco.objects.none(), widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))

    class Meta:
        model = Orcamento
        exclude = ('motivo', 'dt_fat', 'vinc_emp', 'situacao', 'status')
    def __init__(self, *args, empresa=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Inicializa crispy-forms (opcional, se você usa layout personalizado)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field('cli', wrapper_class=''),             # remove mb-3
            Field('tabela_preco', wrapper_class=''),   # remove mb-3
            Field('obs_cli', wrapper_class=''),
        )

        if empresa:
            self.fields['cli'].queryset = Cliente.objects.filter(vinc_emp=empresa)
            self.fields['vinc_fil'].queryset = Filial.objects.filter(vinc_emp=empresa)
            self.fields['solicitante'].queryset = Tecnico.objects.filter(vinc_emp=empresa)
            self.fields['tabela_preco'].queryset = TabelaPreco.objects.filter(vinc_emp=empresa)
            if not self.instance.pk and user and user.filial_user:
                self.fields['vinc_fil'].initial = user.filial_user.pk
                self.fields['cli'].initial = user.filial_user.cli.pk
                self.fields['solicitante'].initial = user.filial_user.tec.pk
                self.fields['tabela_preco'].initial = user.filial_user.tb_preco.pk
            # --- FORMAS DE PAGAMENTO ---
            qs_formas = FormaPgto.objects.filter(vinc_emp=empresa, situacao='Ativo')
            tabela = getattr(self.instance, 'tabela_preco', None)
            if tabela:
                tipo_plano = getattr(tabela, 'tipo', '').lower()
                formas_ambas = ['DINHEIRO', 'CRÉDITO', 'DÉBITO', 'PIX']

                if tipo_plano == 'a vista':
                    qs_formas = qs_formas.filter(
                        models.Q(tipo__iexact='A vista') | models.Q(descricao__in=formas_ambas)
                    )
                else:
                    qs_formas = qs_formas.filter(
                        models.Q(gera_parcelas=True) | models.Q(descricao__in=formas_ambas)
                    )

            self.fields['formas_pgto'].queryset = qs_formas.distinct()

        # --- Inicializa campos derivados com segurança ---
        self.initial['nome_cli'] = getattr(getattr(self.instance, 'cli', None), 'fantasia', '')
        self.initial['nome_solicitante'] = getattr(getattr(self.instance, 'solicitante', None), 'nome', '')

        # --- Formata datas se houver instância existente ---
        if getattr(self.instance, 'pk', None):
            if getattr(self.instance, 'dt_emi', None):
                self.initial['dt_emi'] = self.instance.dt_emi.strftime('%d/%m/%Y')
            if getattr(self.instance, 'dt_ent', None):
                self.initial['dt_ent'] = self.instance.dt_ent.strftime('%d/%m/%Y')

    def clean_obs_cli(self):
        return self.cleaned_data['obs_cli'].upper()

    def clean_obs_form_pgto(self):
        return self.cleaned_data['obs_form_pgto'].upper()

    def clean(self):
        cleaned_data = super().clean()
        forma = cleaned_data.get('formas_pgto')
        tabela = cleaned_data.get('tabela_preco')

        if forma and tabela:
            tipo_plano = tabela.tipo.lower()
            formas_ambas = ['DINHEIRO', 'CRÉDITO', 'DÉBITO', 'PIX']

            if tipo_plano == 'a vista' and not (forma.tipo.lower() == 'a vista' or forma.descricao.upper() in formas_ambas):
                raise forms.ValidationError(f"A forma {forma.descricao} não é permitida para o plano À Vista.")
            elif tipo_plano == 'a prazo' and not (forma.gera_parcelas or forma.descricao.upper() in formas_ambas):
                raise forms.ValidationError(f"A forma {forma.descricao} não é permitida para o plano A Prazo.")

        return cleaned_data

class PortaOrcamentoForm(forms.ModelForm):
    rolo = forms.DecimalField(localize=False)
    largura = forms.DecimalField(localize=False)
    altura = forms.DecimalField(localize=False)
    m2 = forms.DecimalField(localize=False)
    larg_corte = forms.DecimalField(localize=False)
    alt_corte = forms.DecimalField(localize=False)
    class Meta:
        model = PortaOrcamento
        fields = '__all__'
        localized_fields = ('rolo', 'largura', 'altura', 'm2','larg_corte', 'alt_corte')

class PortaProdutoForm(forms.ModelForm):
    quantidade = forms.DecimalField(localize=False)
    class Meta:
        model = PortaProduto
        fields = ('produto', 'quantidade')
        localized_fields = ('quantidade', )

class PortaAdicionalForm(forms.ModelForm):
    quantidade = forms.DecimalField(localize=False)
    class Meta:
        model = PortaAdicional
        fields = ('produto', 'quantidade')
        localized_fields = ('quantidade', )
