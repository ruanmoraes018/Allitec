from django import forms
from .models import Estoque
from filiais.models import Filial

class EstoqueForm(forms.ModelForm):
    descricao = forms.CharField(label='Descrição', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    filial = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Filial')
    class Meta:
        model = Estoque
        exclude = ('empresa',)

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        self.user = kwargs.pop('user', None)

        super().__init__(*args, **kwargs)

        # ============================================================
        # DEFINE A EMPRESA
        # ============================================================

        # Se a empresa não foi passada explicitamente,
        # tenta utilizar a empresa do próprio estoque.
        if (
            not self.empresa
            and self.instance
            and self.instance.pk
            and getattr(self.instance, 'empresa', None)
        ):
            self.empresa = self.instance.empresa

        # ============================================================
        # FILIAIS DA EMPRESA
        # ============================================================

        if self.empresa:

            filiais = (
                Filial.objects
                .filter(vinc_emp=self.empresa)
                .order_by('codigo')
            )

            self.fields['filial'].choices = (
                [('', 'Escolha uma opção')] +
                [
                    (str(f.codigo), f.fantasia.upper())
                    for f in filiais
                ]
            )

            # ========================================================
            # EDIÇÃO
            # ========================================================

            if self.instance and self.instance.pk:

                # Segurança extra:
                # impede carregar um Estoque de outra empresa
                if self.instance.empresa_id != self.empresa.pk:
                    raise forms.ValidationError(
                        'Este estoque não pertence à empresa selecionada.'
                    )

                if self.instance.filial:
                    self.initial['filial'] = str(
                        self.instance.filial.codigo
                    )

            # ========================================================
            # NOVO ESTOQUE
            # ========================================================

            else:

                # Pré-seleciona a filial do usuário logado,
                # desde que ela pertença à empresa atual.
                if self.user and self.user.filial_user:

                    filial_usuario = self.user.filial_user

                    if filial_usuario.vinc_emp_id == self.empresa.pk:
                        self.initial['filial'] = str(
                            filial_usuario.codigo
                        )

        else:
            self.fields['filial'].choices = [
                ('', 'Escolha uma opção')
            ]

    def clean(self):
        cleaned_data = super().clean()

        # ============================================================
        # EMPRESA OBRIGATÓRIA
        # ============================================================

        if not self.empresa:
            raise forms.ValidationError(
                'Empresa não identificada para este cadastro.'
            )

        # ============================================================
        # VALIDAÇÃO DA FILIAL
        # ============================================================

        codigo_filial = cleaned_data.get('filial')

        if codigo_filial:

            try:
                filial = Filial.objects.get(
                    codigo=codigo_filial,
                    vinc_emp=self.empresa
                )

                cleaned_data['filial'] = filial

            except Filial.DoesNotExist:
                self.add_error(
                    'filial',
                    'Filial inválida para esta empresa.'
                )

        else:
            self.add_error(
                'filial',
                'Selecione uma filial.'
            )

        return cleaned_data

    def save(self, commit=True):
        estoque = super().save(commit=False)

        # ============================================================
        # GARANTE O VÍNCULO COM A EMPRESA
        # ============================================================

        estoque.empresa = self.empresa

        if commit:
            estoque.save()

        return estoque