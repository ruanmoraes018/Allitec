import mercadopago
import requests
import json
import base64
from django.conf import settings
from datetime import datetime, timedelta

class PagamentoService:
    def __init__(self, forma_ou_credenciais):
        # 🛡️ Identifica se recebeu o Model FormaPgto ou se recebeu um dicionário direto
        if hasattr(forma_ou_credenciais, 'gateway'):
            # Se for o model completo (como enviado pelo seu fluxo.py)
            self.forma_pgto = forma_ou_credenciais
            self.gateway = (forma_ou_credenciais.gateway or "").strip().lower()
            credenciais_brutas = forma_ou_credenciais.credenciais
        else:
            # Se for um dicionário direto (padrão antigo que seu sistema podia usar)
            self.forma_pgto = None
            credenciais_brutas = forma_ou_credenciais
            # Tenta inferir o gateway por dentro do dicionário ou deixa em branco para o roteador tratar
            self.gateway = "infinitepay" # Força o fallback seguro para o contexto atual

        # 🛡️ Garante que self.creds seja sempre um dicionário limpo
        if isinstance(credenciais_brutas, str):
            try:
                self.creds = json.loads(credenciais_brutas)
            except:
                self.creds = {}
        else:
            self.creds = credenciais_brutas or {}

    def gerar_pagamento(self, valor, descricao, email=None, external_reference=None):
        # Roteador flexível usando o gateway tratado no __init__
        gateway_alvo = self.gateway

        if gateway_alvo == "mercadopago":
            return self._mercadopago(valor, descricao, email, external_reference)
        elif gateway_alvo == "pagbank" or gateway_alvo == "pagseguro":
            return self._pagbank(valor, descricao, email, external_reference)
        elif gateway_alvo == "infinitepay":
            return self._infinitepay(valor, descricao, email, external_reference)

        return None
    # 🔹 MERCADO PAGO
    def _mercadopago(self, valor, descricao, email, external_reference=None):
        token = self.creds.get("access_token")
        if not token: raise Exception("Token não configurado")
        sdk = mercadopago.SDK(token)
        response = sdk.payment().create({
            "transaction_amount": float(valor), "description": descricao, "payment_method_id": "pix", "notification_url": "https://allitec.pythonanywhere.com/pagamentos/webhook/",
            "external_reference": external_reference, "payer": {"email": email}
        })
        resp = response.get("response", {})
        if "id" not in resp: raise Exception(f"Erro MercadoPago: {resp}")
        tx = resp.get("point_of_interaction", {}).get("transaction_data", {})
        return {"id": resp.get("id"), "qr_code": tx.get("qr_code"), "qr_base64": tx.get("qr_code_base64")}
    # 🔹 PAGBANK
    def _pagbank(self, valor, descricao, email=None, cpf=None, external_reference=None):
        token = self.creds.get("token") or self.creds.get("access_token")
        ambiente = self.creds.get("ambiente", "homologacao")
        # Gera a data de expiração dinâmica (60 minutos) no padrão ISO do PagBank
        data_expiracao = (datetime.now() + timedelta(minutes=60)).strftime("%Y-%m-%dT%H:%M:%S-03:00")
        if not token:
            raise Exception("Token PagBank não configurado nas credenciais")
        # Define URL com base no ambiente selecionado no Admin
        if ambiente == "producao":
            url = "https://api.pagseguro.com/orders"
        else:
            url = "https://sandbox.api.pagseguro.com/orders"
        headers = {
            "Authorization": f"Bearer {token}", "Content-Type": "application/json", "accept": "application/json"
        }
        # Converte valor para centavos (ex: 15.90 -> 1590)
        valor_centavos = int(float(valor) * 100)
        # 🧼 TRATAMENTO DE SEGURANÇA DO CPF/CNPJ:
        if cpf:
            # Limpa qualquer pontuação que o cliente tenha digitado no front-end
            tax_id_limpo = "".join(filter(str.isdigit, str(cpf)))
        else:
            tax_id_limpo = ""
        # 🧠 INTELIGÊNCIA DE AMBIENTE:
        # Se estiver em homologação e não veio CPF, injeta o CNPJ de teste que validamos.
        # Se estiver em produção, barra a requisição se o CPF/CNPJ real do comprador estiver ausente.
        if not tax_id_limpo:
            if ambiente != "producao":
                tax_id_limpo = "66643052000194"  # Nosso CNPJ de teste aprovado
            else:
                raise Exception("Erro: O CPF ou CNPJ do cliente é obrigatório para emitir Pix em Produção.")
        payload = {
            "reference_id": str(external_reference or "SEM_REF"),
            "customer": {
                # Se não houver nome do cliente no escopo, usa uma string genérica aceitável
                "name": "Cliente PagBank" if ambiente == "producao" else "Empresa Allitec Teste",
                "email": str(email) if email else "cliente@teste.com",
                "tax_id": tax_id_limpo
            },
            "customer_modifiable": False,
            "qr_codes": [
                {
                    "amount": {"value": valor_centavos},
                    "expiration_date": data_expiracao
                }
            ],
            "notification_urls": [
                "https://allitec.pythonanywhere.com/pagamentos/webhook/"
            ]
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            print(response.status_code)
            print("RESPOSTA PAGBANK:", response.text)
            if response.status_code not in [200, 201]:
                raise Exception(f"Erro PagBank ({response.status_code}): {response.text}")
            data = response.json()
            qr_code_data = data.get("qr_codes", [{}])[0]
            copia_cola = qr_code_data.get("text")
            # Gera o Base64 localmente mantendo a retrocompatibilidade perfeita com o Mercado Pago
            qr_base64 = self._gerar_qr_base64_local(copia_cola)
            return {
                "id": str(external_reference),         # ID da ordem (ORDE_xxxx) para salvar no banco
                "qr_code": copia_cola,         # String Copia e Cola para o cliente copiar
                "qr_base64": qr_base64         # Imagem em Base64 para a tag <img> do front
            }
        except Exception as e:
            raise Exception(f"Falha na comunicação com o PagBank: {str(e)}")

    def _gerar_qr_base64_local(self, payload_pix):
        """Função auxiliar para garantir o retorno em Base64 uniforme"""
        import qrcode
        from io import BytesIO
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(payload_pix)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    # 🔹 INFINITEPAY
    def _infinitepay(self, valor, descricao, email=None, external_reference=None):
        import requests

        handle = self.creds.get("handle")
        if not handle:
            raise Exception("Chave 'handle' não encontrada nas credenciais do gateway.")

        url = "https://api.checkout.infinitepay.io/links"
        headers = {
            "Content-Type": "application/json",
            "accept": "application/json"
        }

        valor_centavos = int(float(valor) * 100)
        clean_handle = str(handle).replace("$", "").strip()

        payload = {
            "handle": clean_handle,
            "webhook_url": "https://allitec.pythonanywhere.com/pagamentos/webhook/",
            "items": [
                {
                    "quantity": 1,
                    "price": valor_centavos,
                    "description": str(descricao)[:60]
                }
            ]
        }

        try:
            # O PythonAnywhere Free vai travar aqui se a URL não estiver liberada por eles
            response = requests.post(url, json=payload, headers=headers, timeout=10)

            if response.status_code not in [200, 201]:
                raise Exception(f"Erro retornado pela InfinitePay ({response.status_code}): {response.text}")

            data = response.json()
            url_checkout = data.get("url") or data.get("checkout_url")
            txid_fatura = data.get("slug") or data.get("invoice_slug")

            return {
                "id": txid_fatura,
                "qr_code": url_checkout,
                "qr_base64": ""
            }

        except Exception as e:
            # 🔥 Forçamos o erro a subir para que a View capture o texto real
            raise Exception(f"Falha de conexão no PythonAnywhere Free: {str(e)}")
    # 🔹 PIX DIRETO (placeholder)
    def _pix_direto(self, valor, descricao, external_reference=None):
        """
        Implementação do PIX Direto via API oficial do Banco (Padrão BACEN)
        Exige autenticação mTLS (com certificado digital)
        """
        # 1. Recuperar as credenciais da forma de pagamento (supondo que sua classe tenha esse acesso)
        # Exemplo: self.forma.client_id, self.forma.certificado_path, etc.
        client_id = getattr(self.forma, "client_id", None)
        client_secret = getattr(self.forma, "client_secret", None)
        cert_path = getattr(self.forma, "certificado_path", None) # Caminho do arquivo .pem no servidor
        chave_pix = getattr(self.forma, "chave_pix", None)
        # URL da API do seu Banco (Exemplo: Sicoob, Sicredi, Itaú, etc.)
        # Geralmente dividida em homologação/produção
        # Define se é produção ou homologação baseado nas configurações salvas
        is_producao = getattr(self.forma, "ambiente", "homologacao") == "producao"
        if is_producao:
            base_url = "https://api.bb.com.br" # URL real de produção do BB
            cert_param = getattr(self.forma, "certificado_path", None)
        else:
            base_url = "https://api.hm.bb.com.br" # URL de homologação do BB
            cert_param = None
        try:
            # 2. Autenticação Oauth2 (mTLS exige o certificado na requisição)
            auth_url = f"{base_url}/oauth/token"
            payload = {"grant_type": "client_credentials", "scope": "cob.write cob.read"}
            # O pulo do gato nos bancos é o parâmetro 'cert', que passa o certificado digital da empresa
            auth_response = requests.post(
                auth_url,
                data=payload,
                auth=(client_id, client_secret),
                cert=cert_path,
                timeout=10
            )
            auth_response.raise_for_status()
            access_token = auth_response.json().get("access_token")
            # Headers padrões para todas as requisições seguintes
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            # 3. Criar a cobrança imediata (/v2/cob)
            cob_url = f"{base_url}/v2/cob"
            # Formata o valor para string com duas casas decimais (exigência do BACEN)
            valor_str = "{:.2f}".format(float(valor))
            cob_payload = {
                "calendario": {
                    "expiracao": 3600 # 1 hora para pagar
                },
                "devedor": {
                    # Opcional: Adicionar CPF/CNPJ se tiver no fluxo
                    "nome": "Cliente Consumidor"
                },
                "valor": {
                    "original": valor_str
                },
                "chave": chave_pix,
                "solicitacaoPagador": descricao[:140] # Limite do campo PIX
            }
            cob_response = requests.post(cob_url, json=cob_payload, cert=cert_path, headers=headers, timeout=10)
            cob_response.raise_for_status()
            cob_dados = cob_response.json()
            # O banco retorna o txid (ID da transação) e o pixCopiaECola (no campo 'pixCopiaECola')
            txid = cob_dados.get("txid")
            pix_copia_e_cola = cob_dados.get("pixCopiaECola")
            # 4. Gerar o QR Code em Base64
            # Alguns bancos já retornam o base64, outros não.
            # Se o banco não retornar, você pode gerar usando a biblioteca local `qrcode` do python:
            qr_base64 = self._gerar_qr_base64_local(pix_copia_e_cola)
            # 5. Retorna EXATAMENTE o mapa que o seu fluxo.py espera ler
            return {
                "id": txid,
                "qr_code": pix_copia_e_cola,
                "qr_base64": qr_base64
            }
        except Exception as e:
            # Adicione um log aqui para rastrear erros de conexão/credenciais
            print(f"Erro no PIX Direto: {str(e)}")
            return None