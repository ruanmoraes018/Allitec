from django.db import transaction
from django.contrib.auth.hashers import make_password
from empresas.models import Empresa
from filiais.models import Filial, Usuario
from clientes.models import Cliente
from tecnicos.models import Tecnico
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado

class EmpresaService:
    @staticmethod
    @transaction.atomic
    def criar_empresa_com_estrutura(form, request_files=None):
        nova_empresa = form.save(commit=False)
        nova_empresa.situacao = 'Ativa'
        logo = request_files.get('logo') if request_files else None
        if logo: nova_empresa.logo = logo
        else: nova_empresa.logo = 'default_logo.png'
        nova_empresa.save()
        filial_criada = None
        # 🔥 LOCALIZAÇÃO + FILIAL + BASE
        if nova_empresa.gerar_filial:
            bairro, _ = Bairro.objects.get_or_create(nome_bairro=nova_empresa.bairro_emp, vinc_emp=nova_empresa)
            cidade, _ = Cidade.objects.get_or_create(nome_cidade=nova_empresa.cidade_emp, vinc_emp=nova_empresa)
            estado, _ = Estado.objects.get_or_create(nome_estado=nova_empresa.uf_emp, vinc_emp=nova_empresa)
            filial_criada, _ = Filial.objects.get_or_create(
                situacao='Ativa', cnpj=nova_empresa.cnpj, ie=nova_empresa.ie, razao_social=nova_empresa.razao_social, fantasia=nova_empresa.fantasia, endereco=nova_empresa.endereco,
                cep=nova_empresa.cep, numero=nova_empresa.numero, bairro_fil=bairro, complem=nova_empresa.complem, cidade_fil=cidade, uf=estado, tel=nova_empresa.tel,
                email=nova_empresa.email, fantasia_normalizado=nova_empresa.fantasia_normalizado, principal=True, logo=nova_empresa.logo, vinc_emp=nova_empresa
            )
            Cliente.objects.get_or_create(
                situacao='Ativo', pessoa="Física", cpf_cnpj='.', ie='.', razao_social='CONSUMIDOR', fantasia='CONSUMIDOR', endereco='.', cep='.', numero='.', bairro=bairro, complem='.',
                cidade=cidade, uf=estado, tel='.', email='.', vinc_emp=nova_empresa
            )
            Tecnico.objects.get_or_create(situacao='Ativo', nome='CONSUMIDOR', endereco='.', cep='.', numero='.', bairro=bairro, cidade=cidade, uf=estado, tel='.', email='.', vinc_emp=nova_empresa)
            # 🔥 USUÁRIO PADRÃO
            if not Usuario.objects.filter(username="allitec", empresa=nova_empresa).exists():
                Usuario.objects.create(username="allitec", empresa=nova_empresa, filial_user=filial_criada, password=make_password("@admin@"), first_name="ALLITEC", is_master=True, is_active=True,)
        return nova_empresa, filial_criada