import mercadopago
from django.conf import settings
from .models import CobrancaPix
from decimal import Decimal

sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

def gerar_pix_lote(mensalidades):

    total = sum((m.valor_total for m in mensalidades), Decimal("0.00"))

    payment_data = {
        "transaction_amount": float(round(total, 2)),
        "description": "Pagamento de mensalidades",
        "payment_method_id": "pix",
        "notification_url": "https://allitec.pythonanywhere.com/mensalidades/webhook/mp/",
        "payer": {"email": "cliente@cliente.com"}
    }

    response = sdk.payment().create(payment_data)
    payment = response["response"]

    cobranca = CobrancaPix.objects.create(
        mp_payment_id=payment["id"],
        qr_code=payment["point_of_interaction"]["transaction_data"]["qr_code"],
        qr_code_base64=payment["point_of_interaction"]["transaction_data"]["qr_code_base64"],
        valor=Decimal(total)
    )

    cobranca.mensalidades.set(mensalidades)

    # salva nas mensalidades
    mensalidades.update(pix_txid=payment["id"])

    return cobranca