
from datetime import date
from django.urls import reverse
from contratos.models import Contrato
from mensalidades.models import Mensalidade


class BloqueioInadimplenciaMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if (
            request.path.startswith('/pedidos/webhook/')
            or request.path.startswith('/mensalidades/webhook/')
        ):
            return self.get_response(request)

        request.bloqueado = False
        request.motivo_bloqueio = ""
        request.aviso_inadimplencia = False
        request.msg_aviso = ""
        request.url_portal = ""

        if not request.user.is_authenticated:
            return self.get_response(request)

        if request.user.is_superuser:
            return self.get_response(request)

        # Permitir o fluxo de acesso e navegação no portal
        rotas_portal = [
            '/mensalidades/acesso-portal/',
            '/mensalidades/portal/',
            '/mensalidades/login/',
        ]

        if any(request.path.startswith(p) for p in rotas_portal):
            return self.get_response(request)

        filial = getattr(request.user, 'filial_user', None)

        if not filial:
            return self.get_response(request)

        empresa = filial.vinc_emp

        # EMPRESA INATIVA
        if filial.situacao != 'Ativa':
            request.bloqueado = True
            request.motivo_bloqueio = (
                "Sua empresa encontra-se INATIVA. Entre em contato com o suporte."
            )
            return self.get_response(request)

        # CONTRATO
        contrato_ativo = Contrato.objects.filter(
            empresa=empresa,
            situacao='Ativo',
            status='Aprovado'
        ).exists()

        if not contrato_ativo:
            request.bloqueado = True
            request.motivo_bloqueio = (
                "Nenhum contrato ativo encontrado para sua empresa."
            )
            return self.get_response(request)

        # MENSALIDADES
        hoje = date.today()

        mensalidades = Mensalidade.objects.filter(
            empresa=empresa,
            situacao='Aberta',
            dt_venc__lt=hoje
        ).order_by('dt_venc')

        for m in mensalidades:

            # ATÉ 5 DIAS -> AVISO
            if 1 <= m.dias_atraso <= 5:

                request.aviso_inadimplencia = True

                request.msg_aviso = (
                    f"Identificamos uma mensalidade em aberto há "
                    f"<b class='text-danger'>{m.dias_atraso} dias</b>.<br>"
                    "Para evitar o bloqueio do sistema, realize o pagamento "
                    "o quanto antes."
                )

            # MAIS DE 5 DIAS -> BLOQUEIO
            if m.dias_atraso > 5:

                request.bloqueado = True

                # URL QUE GERA O TOKEN TEMPORÁRIO
                url_acesso = reverse('acesso_portal_pagamentos')

                link = (
                    f"<a href='{url_acesso}' target='_blank'"
                    f"class='btn btn-danger btn-sm fw-bold mt-2'>"
                    f"<i class='fa-solid fa-credit-card me-1'></i> "
                    f"Acessar portal de pagamentos"
                    f"</a>"
                )

                request.motivo_bloqueio = (
                    f"Existe mensalidade vencida há "
                    f"<span class='text-danger fw-bold'>"
                    f"{m.dias_atraso} dias</span>.<br>"
                    "Regularize o pagamento para continuar utilizando "
                    "o sistema.<br>"
                    f"{link}"
                )

                break

        return self.get_response(request)
