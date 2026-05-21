import os
import json
from django import forms
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import FormaPgto
from core.pagamentos.credenciais import CREDENCIAIS_GATEWAY

c_s = 'form-select form-select-sm border-dark-subtle'
c_f = 'form-control form-control-sm border-dark-subtle'

class FormaPgtoForm(forms.ModelForm):
    situacao = forms.ChoiceField(label="Situação", choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')], widget=forms.Select(attrs={'class': c_s}))
    troco = forms.ChoiceField(label="Permite troco?", choices=[('Não', 'Não'), ('Sim', 'Sim')], widget=forms.Select(attrs={'class': c_s}))
    forma_padrao = forms.ChoiceField(label="Forma Padrão?", choices=[('Não', 'Não'), ('Sim', 'Sim')], widget=forms.Select(attrs={'class': c_s}))
    tipo = forms.ChoiceField(label="Tipo", choices=[('A vista', 'A vista'), ('A prazo', 'A prazo')], widget=forms.Select(attrs={'class': c_s}))
    descricao = forms.CharField(label='Descrição', widget=forms.TextInput(attrs={'class': f'{c_f} text-uppercase'}))
    gera_parcelas = forms.ChoiceField(label='Gera Parcelas?', choices=[(False, 'Não'), (True, 'Sim')], widget=forms.Select(attrs={'class': c_s}))
    gateway = forms.ChoiceField(label="Gateway", choices=FormaPgto._meta.get_field('gateway').choices, widget=forms.Select(attrs={'class': c_s}))
    
    # 🔥 NOVO: Campo de Ambiente (Será injetado dentro do JSON de credenciais)
    ambiente = forms.ChoiceField(
        label="Ambiente", 
        choices=[('homologacao', 'Homologação'), ('producao', 'Produção')], 
        widget=forms.Select(attrs={'class': c_s})
    )
    
    credenciais = forms.CharField(label="Credenciais (JSON)", required=False, widget=forms.Textarea(attrs={'class': c_f, 'rows': 4, 'placeholder': '{"access_token": "..."}'}))

    class Meta:
        model = FormaPgto
        # Adicionado 'ambiente' na lista de campos do Form
        fields = ('situacao', 'troco', 'tipo', 'descricao', 'gera_parcelas', 'gateway', 'ambiente', 'credenciais', 'forma_padrao',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Se estiver editando um registro existente, extrai o ambiente de dentro do JSON antigo para preencher o select
        if self.instance and self.instance.pk and self.instance.credenciais:
            try:
                cred = self.instance.credenciais
                if isinstance(cred, str):
                    cred = json.loads(cred)
                if 'ambiente' in cred:
                    self.initial['ambiente'] = cred['ambiente']
            except Exception:
                pass

    def clean_credenciais(self):
        cred = self.cleaned_data.get("credenciais")
        if not cred: return {}
        if isinstance(cred, dict): return cred
        try: return json.loads(cred)
        except json.JSONDecodeError: raise forms.ValidationError("JSON inválido nas credenciais")

    def clean(self):
        cleaned = super().clean()
        gateway = cleaned.get("gateway")
        ambiente = cleaned.get("ambiente")
        cred = cleaned.get("credenciais") or {}

        # Injeta a escolha do select de ambiente diretamente no dicionário de credenciais
        if ambiente:
            cred["ambiente"] = ambiente

        # Se for pix_direto, validações específicas do certificado e chaves
        if gateway == "pix_direto":
            uploaded_file = self.files.get("certificado_file")
            is_producao = (ambiente == "producao")

            # 🔥 AJUSTE: Validação do certificado só roda se for PRODUÇÃO
            if is_producao:
                if not uploaded_file and not cred.get("certificado_path"):
                    raise forms.ValidationError("O arquivo de Certificado (.pem) é estritamente obrigatório em ambiente de Produção.")

            # Validação dos outros campos de texto do pix_direto (client_id, client_secret, chave_pix)
            # Garantimos que "certificado_path" NUNCA entre nesta lista automatizada em homologação
            obrigatorios = ["client_id", "client_secret", "chave_pix"]
            
            faltando = [c for c in obrigatorios if c not in cred or not cred.get(c)]
            if faltando:
                raise forms.ValidationError(f"Campos obrigatórios faltando: {', '.join(faltando)}")

            # Trata e salva o arquivo se ele foi enviado (válido para ambos os ambientes, caso o usuário queira subir em homologação)
            if uploaded_file:
                pasta_destino = os.path.join('certificados_pix', str(uploaded_file.name))
                caminho_salvo = default_storage.save(pasta_destino, ContentFile(uploaded_file.read()))
                caminho_absoluto = os.path.join(settings.MEDIA_ROOT, caminho_salvo)
                
                cred["certificado_path"] = caminho_absoluto

        # Atualiza o cleaned_data final com o dicionário de credenciais modificado
        cleaned["credenciais"] = cred
        return cleaned