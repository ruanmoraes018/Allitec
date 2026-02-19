def financeiro_status(request):
    return {
        'bloqueado': getattr(request, 'bloqueado', False),
        'motivo_bloqueio': getattr(request, 'motivo_bloqueio', ''),
        'aviso_inadimplencia': getattr(request, 'aviso_inadimplencia', False),
        'msg_aviso': getattr(request, 'msg_aviso', ''),
    }
