from django.contrib import messages

def aplicar_filtro_filial(request, queryset, campo="vinc_fil"):
    usuario = request.user
    fil = request.GET.get("fil")
    # Usuário vê todas as filiais
    if usuario.opfilial == "1":
        if fil:
            queryset = queryset.filter(**{f"{campo}__codigo": fil})
        return queryset, False
    # Usuário possui acesso restrito às filiais permitidas
    filiais = usuario.filiais_permitidas.all()
    queryset = queryset.filter(**{f"{campo}__in": filiais})
    if not fil:
        messages.info(request, "Selecione uma filial para consultar os dados.")
        return queryset.none(), True
    queryset = queryset.filter(**{f"{campo}__codigo": fil})
    return queryset, False