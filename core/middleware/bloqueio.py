from datetime import date
from contratos.models import Contrato
from mensalidades.models import Mensalidade

class BloqueioInadimplenciaMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        request.bloqueado = False
        request.motivo_bloqueio = ""
        request.aviso_inadimplencia = False
        request.msg_aviso = ""

        if not request.user.is_authenticated:
            return self.get_response(request)

        if request.user.is_superuser:
            return self.get_response(request)

        filial = getattr(request.user, 'filial_user', None)

        if not filial:
            return self.get_response(request)

        empresa = filial.vinc_emp

        # -------------------------
        # EMPRESA INATIVA
        # -------------------------
        if filial.situacao != 'Ativa':
            request.bloqueado = True
            request.motivo_bloqueio = "Sua empresa encontra-se INATIVA. Entre em contato com o suporte."
            return self.get_response(request)

        # -------------------------
        # CONTRATO
        # -------------------------
        contrato_ativo = Contrato.objects.filter(
            empresa=empresa,
            situacao='Ativo',
            status='Aprovado'
        ).exists()

        if not contrato_ativo:
            request.bloqueado = True
            request.motivo_bloqueio = "Nenhum contrato ativo encontrado para sua empresa."
            return self.get_response(request)

        # -------------------------
        # MENSALIDADE ATRASADA
        # -------------------------
        hoje = date.today()

        request.aviso_inadimplencia = False
        request.msg_aviso = ""

        mensalidades = Mensalidade.objects.filter(
            empresa=empresa,
            situacao='Aberta',
            dt_venc__lt=hoje
        )

        for m in mensalidades:

            # ATÉ 5 DIAS -> AVISO
            if 1 <= m.dias_atraso <= 5:
                request.aviso_inadimplencia = True
                request.msg_aviso = (
                    f"Identificamos uma mensalidade em aberto há "
                    f"<b class='text-danger'>{m.dias_atraso} dias</b>.<br>"
                    "Para evitar o bloqueio do sistema, realize o pagamento o quanto antes."
                )

            # MAIOR QUE 5 -> BLOQUEIO
            if m.dias_atraso > 5:
                request.bloqueado = True
                request.motivo_bloqueio = (
                    f"Existe mensalidade vencida há <span class='text-danger fw-bold'>{m.dias_atraso} dias</span>. "
                    "Regularize o pagamento para continuar utilizando o sistema."
                )
                break


        return self.get_response(request)
