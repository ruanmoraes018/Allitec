import mercadopago
from pedidos.models import Pagamento

def tratar_webhook_mercadopago(data):

    payment_id = data.get("data", {}).get("id")
    if not payment_id:
        return None

    # 🔥 busca o pagamento no seu sistema
    pagamento = Pagamento.objects.filter(
        txid=str(payment_id)
    ).select_related('forma_pgto').first()

    if not pagamento:
        return None

    forma = pagamento.forma_pgto

    # 🔥 pega credenciais da forma
    credenciais = forma.credenciais or {}

    access_token = credenciais.get("access_token")

    if not access_token:
        return None

    # 🔥 cria SDK dinâmico
    sdk = mercadopago.SDK(access_token)

    # 🔥 consulta API real
    payment_info = sdk.payment().get(payment_id)["response"]

    status = payment_info.get("status")

    return {
        "txid": str(payment_id),
        "status": "pago" if status == "approved" else status
    }

def tratar_webhook_pix_direto(data):
    # padrão BACEN
    pix = data.get("pix", [])
    if not pix:
        return None
    item = pix[0]
    return {"txid": item.get("txid"), "status": "pago"}

def identificar_gateway(request, data):
    # tentativa simples (pode melhorar depois)
    if "type" in data:
        return "mercadopago"
    if "pix" in data:
        return "pix_direto"
    return None

def processar_webhook(request):
    import json
    data = json.loads(request.body)
    gateway = identificar_gateway(request, data)
    if gateway == "mercadopago":
        result = tratar_webhook_mercadopago(data)
    elif gateway == "pix_direto":
        result = tratar_webhook_pix_direto(data)
    else:
        return None
    if not result:
        return None
    # 🔥 adiciona gateway no retorno
    result["gateway"] = gateway
    return result