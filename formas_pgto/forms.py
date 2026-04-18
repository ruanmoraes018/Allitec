from django import forms
from .models import FormaPgto
from core.pagamentos.credenciais import CREDENCIAIS_GATEWAY
import json

c_s = 'form-select form-select-sm border-dark-subtle'
c_f = 'form-control form-control-sm border-dark-subtle'
class FormaPgtoForm(forms.ModelForm):
    situacao = forms.ChoiceField(
        label="Situação",
        choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')],
        widget=forms.Select(attrs={'class': c_s})
    )

    troco = forms.ChoiceField(
        label="Permite troco?",
        choices=[('Não', 'Não'), ('Sim', 'Sim')],
        widget=forms.Select(attrs={'class': c_s})
    )

    tipo = forms.ChoiceField(
        label="Tipo",
        choices=[('A vista', 'A vista'), ('A prazo', 'A prazo')],
        widget=forms.Select(attrs={'class': c_s})
    )

    descricao = forms.CharField(
        label='Descrição',
        widget=forms.TextInput(attrs={'class': c_f})
    )

    gera_parcelas = forms.ChoiceField(
        label='Gera Parcelas?',
        choices=[(False, 'Não'), (True, 'Sim')],
        widget=forms.Select(attrs={'class': c_s})
    )

    # 🔥 NOVO
    gateway = forms.ChoiceField(
        label="Gateway",
        choices=FormaPgto._meta.get_field('gateway').choices,
        widget=forms.Select(attrs={'class': c_s})
    )

    # 🔥 JSON como texto (mais fácil no admin)
    credenciais = forms.CharField(
        label="Credenciais (JSON)",
        required=False,
        widget=forms.Textarea(attrs={
            'class': c_f,
            'rows': 4,
            'placeholder': '{"access_token": "..."}'
        })
    )

    class Meta:
        model = FormaPgto
        fields = (
            'situacao',
            'troco',
            'tipo',
            'descricao',
            'gera_parcelas',
            'gateway',
            'credenciais'
        )

    def clean_credenciais(self):
        cred = self.cleaned_data.get("credenciais")

        # 🔥 se vier vazio, retorna dict vazio
        if not cred:
            return {}

        # 🔥 se já for dict (às vezes acontece), retorna direto
        if isinstance(cred, dict):
            return cred

        try:
            return json.loads(cred)
        except json.JSONDecodeError:
            raise forms.ValidationError("JSON inválido nas credenciais")

    def clean(self):
        cleaned = super().clean()

        gateway = cleaned.get("gateway")
        cred = cleaned.get("credenciais") or {}

        if gateway and gateway != "nenhum":
            obrigatorios = CREDENCIAIS_GATEWAY.get(gateway, [])

            faltando = [
                c for c in obrigatorios
                if c not in cred or not cred.get(c)
            ]

            if faltando:
                raise forms.ValidationError(
                    f"Campos obrigatórios: {', '.join(faltando)}"
                )

        return cleaned