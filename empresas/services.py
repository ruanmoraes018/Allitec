from django.db import transaction
from django.contrib.auth.hashers import make_password
from empresas.models import Empresa
from filiais.models import Filial, Usuario
from clientes.models import Cliente
from tecnicos.models import Tecnico
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado
from unidades.models import Unidade
from formas_pgto.models import FormaPgto
from tabelas_preco.models import TabelaPreco
from vendedores.models import Vendedor

unidades = ['UN', 'M²', 'ML', 'KG']
formas = ['DINHEIRO', 'CRÉDITO', 'DÉBITO', 'PIX', 'CREDIÁRIO']
tabelas = ['AVISTA', 'APRAZO']

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
        if nova_empresa.gerar_filial:
            bairro, _ = Bairro.objects.get_or_create(nome_bairro=nova_empresa.bairro_emp, vinc_emp=nova_empresa)
            cidade, _ = Cidade.objects.get_or_create(nome_cidade=nova_empresa.cidade_emp, vinc_emp=nova_empresa)
            estado, _ = Estado.objects.get_or_create(nome_estado=nova_empresa.uf_emp, vinc_emp=nova_empresa)
            # Geração de Filial
            filial_criada, _ = Filial.objects.get_or_create(
                cnpj=nova_empresa.cnpj,
                vinc_emp=nova_empresa,
                defaults={
                    'situacao': 'Ativa',
                    'ie': nova_empresa.ie,
                    'razao_social': nova_empresa.razao_social,
                    'fantasia': nova_empresa.fantasia,
                    'endereco': nova_empresa.endereco,
                    'cep': nova_empresa.cep,
                    'numero': nova_empresa.numero,
                    'bairro_fil': bairro,
                    'complem': nova_empresa.complem,
                    'cidade_fil': cidade,
                    'uf': estado,
                    'tel': nova_empresa.tel,
                    'fantasia_normalizado': nova_empresa.fantasia_normalizado,
                    'principal': True,
                    'logo': nova_empresa.logo,
                }
            )
            # Geração de Cliente Padrão
            Cliente.objects.get_or_create(
                cpf_cnpj='080.681.140-41',
                vinc_emp=nova_empresa,
                defaults={
                    'situacao': 'Ativo',
                    'pessoa': 'Física',
                    'ie': '0',
                    'razao_social': 'CONSUMIDOR',
                    'fantasia': 'CONSUMIDOR',
                    'endereco': nova_empresa.endereco,
                    'cep': nova_empresa.cep,
                    'numero': nova_empresa.numero,
                    'bairro': bairro,
                    'complem': nova_empresa.complem,
                    'cidade': cidade,
                    'uf': estado,
                    'tel': nova_empresa.tel,
                    'email': nova_empresa.email,
                }
            )
            # Geração de Vendedor Padrão
            Vendedor.objects.get_or_create(
                cpf_cnpj='080.681.140-41',
                vinc_emp=nova_empresa,
                defaults={
                    'situacao': 'Ativo',
                    'pessoa': 'Física',
                    'ie': '0',
                    'razao_social': 'DIVERSOS',
                    'fantasia': 'DIVERSOS',
                    'endereco': nova_empresa.endereco,
                    'cep': nova_empresa.cep,
                    'numero': nova_empresa.numero,
                    'bairro': bairro,
                    'complem': nova_empresa.complem,
                    'cidade': cidade,
                    'uf': estado,
                    'tel': nova_empresa.tel,
                    'email': nova_empresa.email,
                }
            )
            # Geração de Técnico Padrão
            Tecnico.objects.get_or_create(
                nome='DIVERSOS',
                vinc_emp=nova_empresa,
                defaults={
                    'situacao': 'Ativo',
                    'endereco': nova_empresa.endereco,
                    'cep': nova_empresa.cep,
                    'numero': nova_empresa.numero,
                    'bairro': bairro,
                    'cidade': cidade,
                    'uf': estado,
                    'tel': nova_empresa.tel,
                    'email': nova_empresa.email,
                }
            )
            # Geração de Unidades
            for u in unidades:
                Unidade.objects.get_or_create(nome_unidade=u, vinc_emp=nova_empresa)
            # Geração de Formas de Pagamento
            for f in formas:
                if f == 'DINHEIRO':
                    FormaPgto.objects.get_or_create(
                        descricao=f,
                        vinc_emp=nova_empresa,
                        defaults={
                            'situacao': 'Ativo',
                            'troco': 'Sim',
                            'forma_padrao': 'Sim',
                            'tipo': 'A vista',
                            'gateway': 'nenhum',
                            'credenciais': {},
                        }
                    )
                elif f == 'CREDIÁRIO':
                    FormaPgto.objects.get_or_create(
                        descricao=f,
                        vinc_emp=nova_empresa,
                        defaults={
                            'situacao': 'Ativo',
                            'troco': 'Não',
                            'forma_padrao': 'Não',
                            'tipo': 'A prazo',
                            'gateway': 'nenhum',
                            'credenciais': {},
                        }
                    )
                else:
                    FormaPgto.objects.get_or_create(
                        descricao=f,
                        vinc_emp=nova_empresa,
                        defaults={
                            'situacao': 'Ativo',
                            'troco': 'Não',
                            'forma_padrao': 'Não',
                            'tipo': 'A vista',
                            'gateway': 'nenhum',
                            'credenciais': {},
                        }
                    )
            # Geração de Tabela de Preço
            for t in tabelas:
                TabelaPreco.objects.get_or_create(
                    descricao=t,
                    vinc_emp=nova_empresa,
                    defaults={
                        'margem': 50,
                        'tipo': 'A vista' if t == 'AVISTA' else 'A prazo',
                    }
                )
            # Usuário Padrão
            if not Usuario.objects.filter(username="allitec", empresa=nova_empresa).exists():
                Usuario.objects.create(
                    username="allitec",
                    empresa=nova_empresa,
                    filial_user=filial_criada,
                    password=make_password("@admin@"),
                    first_name="ALLITEC",
                    is_master=True,
                    is_active=True,
                )
        return nova_empresa, filial_criada