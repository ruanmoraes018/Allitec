import mercadopago
import json


class PagamentoService:

    def __init__(self, forma_pgto, origem=None):
        self.forma = forma_pgto
        self.gateway = (forma_pgto.gateway or "").strip().lower()
        self.origem = origem

        creds = forma_pgto.credenciais or {}

        if isinstance(creds, str):
            try:
                creds = json.loads(creds)
            except:
                creds = {}

        self.creds = creds

    # 🔹 MÉTODO PRINCIPAL
    def gerar_pagamento(self, valor, descricao, email, external_reference=None):

        if self.gateway == 'mercadopago':
            return self._mercadopago(valor, descricao, email, external_reference)

        if self.gateway == 'pix_direto':
            return self._pix_direto(valor, descricao)

        raise Exception("Gateway não suportado")

    # 🔹 MERCADO PAGO
    def _mercadopago(self, valor, descricao, email, external_reference=None):

        token = self.creds.get("access_token")
        if not token:
            raise Exception("Token não configurado")

        sdk = mercadopago.SDK(token)

        response = sdk.payment().create({
            "transaction_amount": float(valor),
            "description": descricao,
            "payment_method_id": "pix",

            # 🔥 URL ÚNICA (correto agora)
            "notification_url": "https://allitec.pythonanywhere.com/pagamentos/webhook/mp/",

            "external_reference": external_reference,
            "payer": {
                "email": email
            }
        })

        resp = response.get("response", {})

        if "id" not in resp:
            raise Exception(f"Erro MercadoPago: {resp}")

        tx = resp.get("point_of_interaction", {}).get("transaction_data", {})

        return {
            "id": resp.get("id"),
            "qr_code": tx.get("qr_code"),
            "qr_base64": tx.get("qr_code_base64")
        }

    # 🔹 PIX DIRETO (placeholder)
    def _pix_direto(self, valor, descricao):
        return {
            "msg": "PIX direto ainda não implementado"
        }