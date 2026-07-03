from django import forms
from .models import Proposta
from util.parse_decimal import parse_decimal

class PropostaForm(forms.ModelForm):
    desc_imp = forms.CharField(label='Descrição da Implantação', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    qtd_usu = forms.IntegerField(label='Nº Usuários', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    vl_imp = forms.CharField(label='Valor Implantação', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'placeholder': '0,00', 'style': 'color: #2E8B57; font-weight: bold;'}))
    dsct_imp = forms.CharField(label='Desconto Implantação', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'placeholder': '0,00', 'style': 'color: #2E8B57; font-weight: bold;'}))
    vl_fin_imp = forms.CharField(label='Valor Final', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'placeholder': '0,00', 'style': 'color: #2E8B57; font-weight: bold;'}))
    desc_ass = forms.CharField(label='Descrição da Assessoria', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    vl_ass = forms.CharField(label='Valor Assessoria', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'placeholder': '0,00', 'style': 'color: #2E8B57; font-weight: bold;'}))
    qtd_ass = forms.IntegerField(label='Nº Assesoria', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    dsct_ass = forms.CharField(label='Desconto Assessoria', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'placeholder': '0,00', 'style': 'color: #2E8B57; font-weight: bold;'}))
    vl_fin_ass = forms.CharField(label='Valor Final', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'placeholder': '0,00', 'style': 'color: #2E8B57; font-weight: bold;'}))
    nome_emp = forms.CharField(label='Empresa', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    obs = forms.CharField(
        label='Observações',
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control form-control-sm border-dark-subtle text-uppercase'})
    )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if self.instance.dt_emi: self.initial['dt_emi'] = self.instance.dt_emi.strftime('%d/%m/%Y')
        if getattr(self.instance, 'pk', None):
            if getattr(self.instance, 'dt_emi', None): self.initial['dt_emi'] = self.instance.dt_emi.strftime('%d/%m/%Y')
    def clean(self):
        cleaned_data = super().clean()
        try: cleaned_data['vl_imp'] = parse_decimal(cleaned_data.get('vl_imp'))
        except: self.add_error('vl_imp', 'Valor inválido.')
        try: cleaned_data['dsct_imp'] = parse_decimal(cleaned_data.get('dsct_imp'))
        except: self.add_error('dsct_imp', 'Valor inválido.')
        try: cleaned_data['vl_fin_imp'] = parse_decimal(cleaned_data.get('vl_fin_imp'))
        except: self.add_error('vl_fin_imp', 'Valor inválido.')
        try: cleaned_data['vl_ass'] = parse_decimal(cleaned_data.get('vl_ass'))
        except: self.add_error('vl_ass', 'Valor inválido.')
        try: cleaned_data['dsct_ass'] = parse_decimal(cleaned_data.get('dsct_ass'))
        except: self.add_error('dsct_ass', 'Valor inválido.')
        try: cleaned_data['vl_fin_ass'] = parse_decimal(cleaned_data.get('vl_fin_ass'))
        except: self.add_error('vl_fin_ass', 'Valor inválido.')
        return cleaned_data
    class Meta:
        model = Proposta
        exclude = ('situacao', 'data_confirmacao', 'dt_emi')