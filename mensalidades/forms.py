from django import forms
from util.parse_decimal import parse_decimal
from .models import Mensalidade
from empresas.models import Empresa

s = "form-select form-select-sm border-dark-subtle"
c = "form-control form-control-sm border-dark-subtle"
class MensalidadeForm(forms.ModelForm):
    num_mens = forms.CharField(label='Nr. Mensal.', required=False, widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control bg-secondary-subtle'}))
    empresa = forms.ModelChoiceField(queryset=Empresa.objects.all(), widget=forms.Select( attrs={'class': s}), label='Empresa')
    situacao = forms.ChoiceField(label="Situação", choices=[('Aberta', 'Aberta'), ('Baixada', 'Baixada')], widget=forms.Select(attrs={'class': s}))
    tp_mens = forms.ChoiceField(label="Tp. Mensal.", choices=[('Boleto', 'Boleto'), ('Pix', 'Pix')], widget=forms.Select(attrs={'class': s}))
    dt_venc = forms.DateField(label='Dt. Venci.', input_formats=['%d/%m/%Y'], widget=forms.TextInput(attrs={'class': c}))
    dt_pag = forms.DateField(label='Dt. Pagamento', required=False, input_formats=['%d/%m/%Y'], widget=forms.TextInput(attrs={'class': c}))
    vl_mens = forms.CharField(label='Fator Juros',widget=forms.TextInput(attrs={'class':f'{c} text-end text-white fw-bold','placeholder':'0,00','style':'background-color: #2E8B57;'}))
    tp_juros = forms.ChoiceField(label="Tp. Juros", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], widget=forms.Select(attrs={'class': s}))
    tp_multa = forms.ChoiceField(label="Tp. Multa", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], widget=forms.Select(attrs={'class': s}))
    vl_multa = forms.CharField(label='Vl. Multa', widget=forms.TextInput(attrs={'class': f'{c} text-end fw-bold'}))
    vl_juros = forms.CharField(label='Vl. Juros', widget=forms.TextInput(attrs={'class': f'{c} text-end fw-bold'}))
    obs = forms.CharField(label='Observações', required=False, widget=forms.Textarea(attrs={'class': f'{c} text-uppercase', 'rows': 2}))

    class Meta:
        model = Mensalidade
        exclude = ('created_at', 'updated_at', 'vl_pago')
        widgets = {'dt_venc': forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle',}),}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if self.instance.dt_venc:
                self.initial['dt_venc'] = self.instance.dt_venc.strftime('%d/%m/%Y')

    def clean(self):
        cleaned_data = super().clean()
        campos = ['vl_mens', 'vl_multa', 'vl_juros']
        for c in campos:
            try: cleaned_data[c] = parse_decimal(cleaned_data.get(c))
            except: self.add_error(c, 'Valor inválido.')
        return cleaned_data