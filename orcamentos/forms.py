from django import forms
from .models import Orcamento
from clientes.models import Cliente
from tecnicos.models import Tecnico
from decimal import Decimal, InvalidOperation
from formas_pgto.models import FormaPgto
from filiais.models import Filial

class OrcamentoForm(forms.ModelForm):
    cli = forms.ModelChoiceField(
        label='Cliente',
        queryset=Cliente.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm border-dark-subtle',
        })
    )
    vinc_fil = forms.ModelChoiceField(
        label='Filial',
        queryset=Filial.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm border-dark-subtle',
        })
    )
    obs_cli = forms.CharField(
        label='Obs',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control form-control-sm border-dark-subtle text-uppercase',
            'rows': 2
        })
    )
    num_orcamento = forms.CharField(
        label='Nº',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
            'disabled': 'disabled'
        })
    )
    solicitante = forms.ModelChoiceField(
        label='Técnico/Solicitante',
        queryset=Tecnico.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm border-dark-subtle',
        })
    )

    qtd = forms.CharField(
        label="Quantidade",
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
        })
    )

    qtd_lam = forms.DecimalField(
        label="Qtd. Lâmina",
        max_digits=10,
        decimal_places=2,
        widget=forms.TextInput(attrs={
            'class': 'form-control border-dark-subtle',
            'placeholder': '0.00',
        })
    )

    tp_lamina = forms.ChoiceField(
        label='TP. Lâmina',
        choices=[
            ('Fechada', 'Fechada'),
            ('Transvision', 'Transvision')
        ],
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm border-dark-subtle',
        })
    )

    tp_vao = forms.ChoiceField(
        label='TP. Vão',
        choices=[
            ('Dentro do Vão', 'Dentro do Vão'),
            ('Fora do Vão', 'Fora do Vão'),
            ('1 Lado Dentro do Vão', '1 Lado Dentro do Vão')

        ],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'})
    )
    larg = forms.CharField(
        label='Largura',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
        })
    )
    alt = forms.CharField(
        label='Altura',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
        })
    )
    pintura = forms.ChoiceField(
        choices=[
            ('Sim', 'Sim'),
            ('Não', 'Não')
        ],
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm border-dark-subtle',
        })
    )
    tp_pintura = forms.ChoiceField(
        label="TP. Pintura",
        choices=[
            ('Eletrostática', 'Eletrostática'),
            ('Automotiva', 'Automotiva')
        ],
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm border-dark-subtle',
        })
    )
    cor = forms.ChoiceField(
        choices = [
            ('', ''), ('Preto', 'Preto'), ('Branco', 'Branco'),
            ('Amarelo', 'Amarelo'), ('Vermelho', 'Vermelho'),
            ('Roxo Açaí', 'Roxo Açaí'), ('Azul Pepsi', 'Azul Pepsi'),
            ('Azul Claro', 'Azul Claro'), ('Cinza Claro', 'Cinza Claro'),
            ('Cinza Grafite', 'Cinza Grafite'), ('Verde', 'Verde'),
            ('Bege', 'Bege'), ('Bege Areia', 'Bege Areia'),
            ('Marrom', 'Marrom'), ('Marrom Café', 'Marrom Café'),
            ('Laranja', 'Laranja'), ('Azul Royal', 'Azul Royal'),
            ('Azul Marinho', 'Azul Marinho'), ('Verde Musgo', 'Verde Musgo'),
            ('Verde Bandeira', 'Verde Bandeira'), ('Vinho', 'Vinho'), ('Prata', 'Prata'),
        ],
        required=False,  # Define que o campo não é obrigatório
        widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'})
    )
    fator_peso = forms.CharField(
        label='Fator Peso',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
            'placeholder': '0.00',
        })
    )
    peso = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
            'placeholder': '0.00',
        })
    )
    eixo_motor = forms.CharField(
        label='Eixo Motor',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
            'placeholder': '0.00',
        })
    )
    larg_corte = forms.CharField(
        label='Lg. Corte',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
        })
    )
    alt_corte = forms.CharField(
        label='At. Corte',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
        })
    )
    rolo = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
        })
    )
    m2 = forms.CharField(
        label='M²',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
        })
    )
    obs_form_pgto = forms.CharField(
        label='Obs',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control form-control-sm border-dark-subtle text-uppercase',
            'rows': 2
        })
    )
    desconto = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.TextInput(attrs={
            'class': 'form-control border-dark-subtle',
            'style': 'color: #2E8B57; font-weight: bold; background-color: #808080;',
            'placeholder': '0.00',
            'readonly': 'readonly'  # <-- campo somente leitura
        })
    )

    acrescimo = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.TextInput(attrs={
            'class': 'form-control border-dark-subtle',
            'style': 'color: #2E8B57; font-weight: bold; background-color: #808080;',
            'placeholder': '0.00',
            'readonly': 'readonly'  # <-- campo somente leitura
        })
    )

    dt_emi = forms.DateField(
        label='Dt. Emissão',
        input_formats=['%d/%m/%Y'],
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
        })
    )
    dt_ent = forms.DateField(
        label='Dt. Entrega',
        required=False,
        input_formats=['%d/%m/%Y'],
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
        })
    )
    subtotal = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
            'hidden': ''
        })

    )
    total = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
            'hidden': ''
        })
    )
    formas_pgto = forms.ModelChoiceField(
        label='Formas de Pagamento',
        required=False,
        queryset=FormaPgto.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm border-dark-subtle',
        })
    )


    class Meta:
        model = Orcamento
        fields = (
            'num_orcamento', 'solicitante', 'dt_emi', 'cli',  'obs_cli', 'qtd', 'tp_lamina', 'larg', 'alt', 'tp_vao', 'tp_pintura',
            'pintura', 'cor', 'fator_peso', 'peso', 'eixo_motor', 'larg_corte', 'alt_corte', 'rolo', 'm2', 'obs_form_pgto', 'dt_ent',
            'subtotal', 'total', 'desconto', 'acrescimo', 'vinc_fil', 'qtd_lam'
        )
        widgets = {
            'dt_emi': forms.TextInput(attrs={
                'class': 'form-control form-control-sm border-dark-subtle',
            }),
            'dt_ent': forms.TextInput(attrs={
                'class': 'form-control form-control-sm border-dark-subtle',
            }),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Formatar os valores se o form está sendo carregado com uma instância
        if self.instance and self.instance.pk:
            if self.instance.dt_emi:
                self.initial['dt_emi'] = self.instance.dt_emi.strftime('%d/%m/%Y')
            if self.instance.dt_ent:
                self.initial['dt_ent'] = self.instance.dt_ent.strftime('%d/%m/%Y')

    def clean_obs_cli(self):
        return self.cleaned_data['obs_cli'].upper()

    def clean_obs_form_pgto(self):
        return self.cleaned_data['obs_form_pgto'].upper()