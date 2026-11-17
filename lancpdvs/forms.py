from django import forms
from .models import Caixa
from filiais.models import Filial
from pdvs.models import PDV
from formas_pgto.models import FormaPgto

class CaixaForm(forms.ModelForm):
    terminal = forms.ChoiceField(label='PDV', widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    observacao = forms.CharField(label='Observação', required=False, widget=forms.Textarea(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'rows': 1}))
    class Meta:
        model = Caixa
        fields = ('observacao', 'terminal')

    def __init__(self, *args, **kwargs):
        # Captura e remove a empresa dos kwargs de forma segura
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if not self.empresa and self.instance and self.instance.pk and getattr(self.instance, 'vinc_emp', None):
            self.empresa = self.instance.empresa
        if self.empresa:
            pdvs = PDV.objects.filter(vinc_emp=self.empresa)
            self.fields['terminal'].choices = [('', 'Escolha uma opção')] + [(str(p.codigo), p.nome.upper()) for p in pdvs]
            formas = FormaPgto.objects.filter(vinc_emp=self.empresa)
            for forma in formas:
                self.fields[f'forma_{forma.id}'] = forms.DecimalField(label=forma.descricao, required=False, initial=0, widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}))
            if self.instance and self.instance.pk:
                if self.instance.terminal: self.initial['terminal'] = str(self.instance.terminal.codigo)
        else:
            self.fields['terminal'].choices = [('', 'Escolha uma opção')]

    def clean(self):
        cleaned_data = super().clean()
        # Mapeamento genérico: 'nome_no_form': (ClasseDoModel, 'Nome Amigável para o Erro')
        campos_select2 = {'terminal': (PDV, 'PDV'), }
        for nome_campo, (model_classe, nome_exibicao) in campos_select2.items():
            codigo = cleaned_data.get(nome_campo)
            # Se o usuário preencheu o campo, fazemos a conversão genérica
            if codigo:
                try:
                    objeto_real = model_classe.objects.get(codigo=codigo, vinc_emp=self.empresa)
                    cleaned_data[nome_campo] = objeto_real  # Substitui o código string pelo objeto do banco
                except model_classe.DoesNotExist:
                    self.add_error(nome_campo, f"{nome_exibicao} inválido(a) para esta empresa.")
        return cleaned_data