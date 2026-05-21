import mercadopago
import requests
import json
import base64
from django.conf import settings

class PagamentoService:
    def __init__(self, forma_pgto, origem=None):
        self.forma = forma_pgto
        self.gateway = (forma_pgto.gateway or "").strip().lower()
        self.origem = origem
        creds = forma_pgto.credenciais or {}
        if isinstance(creds, str):
            try: creds = json.loads(creds)
            except: creds = {}
        self.creds = creds
    # 🔹 MÉTODO PRINCIPAL
    def gerar_pagamento(self, valor, descricao, email, external_reference=None):
        if self.gateway == 'mercadopago': return self._mercadopago(valor, descricao, email, external_reference)
        elif self.gateway == 'pagseguro': return self._pagbank(valor, descricao, external_reference)
        elif self.gateway == "pix_direto":
            # Passa os parâmetros necessários para o método novo
            return self._pix_direto(valor, descricao, external_reference)
        raise Exception("Gateway não suportado")
    # 🔹 MERCADO PAGO
    def _mercadopago(self, valor, descricao, email, external_reference=None):
        token = self.creds.get("access_token")
        if not token: raise Exception("Token não configurado")
        sdk = mercadopago.SDK(token)
        response = sdk.payment().create({
            "transaction_amount": float(valor), "description": descricao, "payment_method_id": "pix", "notification_url": "https://allitec.pythonanywhere.com/pagamentos/webhook/mp/",
            "external_reference": external_reference, "payer": {"email": email}
        })
        resp = response.get("response", {})
        if "id" not in resp: raise Exception(f"Erro MercadoPago: {resp}")
        tx = resp.get("point_of_interaction", {}).get("transaction_data", {})
        return {"id": resp.get("id"), "qr_code": tx.get("qr_code"), "qr_base64": tx.get("qr_code_base64")}
    # 🔹 PAGBANK
    def _pagbank(self, valor, descricao, external_reference=None):
        token = self.creds.get("token") or self.creds.get("access_token")
        ambiente = self.creds.get("ambiente", "homologacao")

        if not token:
            raise Exception("Token PagBank não configurado nas credenciais")

        if ambiente == "producao":
            url = "https://api.pagseguro.com/orders"
        else:
            url = "https://sandbox.api.pagseguro.com/orders"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "accept": "application/json"
        }

        # 🔥 PagBank exige valor em CENTAVOS (Ex: 10.50 vira 1050)
        valor_centavos = int(float(valor) * 100)

        payload = {
            "reference_id": str(external_reference or "SEM_REF"),
            "customer_modifiable": False,
            "qr_codes": [
                {
                    "amount": {"value": valor_centavos},
                    # Validade de 60 minutos para o Pix
                    "expiration_date": "2026-05-21T23:59:59-03:00"
                }
            ],
            "notification_urls": [
                "https://allitec.pythonanywhere.com/webhook/pagbank/"
            ]
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)

            if response.status_code not in [200, 201]:
                raise Exception(f"Erro PagBank ({response.status_code}): {response.text}")

            data = response.json()
            qr_code_data = data.get("qr_codes", [{}])[0]

            copia_cola = qr_code_data.get("text")
            qrcode_url = qr_code_data.get("links", [{}])[0].get("href")

            # Em vez de forçar o front a ler um link e um base64 de formas diferentes,
            # nós geramos o Base64 localmente a partir do copia_cola para manter o padrão perfeito!
            qr_base64 = self._gerar_qr_base64_local(copia_cola)

            # Retorna no EXATO padrão que o Mercado Pago usa
            return {
                "id": data.get("id"),          # ID do pedido no PagBank (ORD-xxxx)
                "qr_code": copia_cola,         # Chave Copia e Cola
                "qr_base64": qr_base64         # Imagem convertida em string base64
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