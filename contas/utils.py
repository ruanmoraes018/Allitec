def ordenar_permissoes(permissoes, ordem):
    return sorted(
        permissoes,
        key=lambda p: ordem.index(p.codename) if p.codename in ordem else 999
    )


def agrupar_permissoes(permissoes, grupos):
    resultado = {k: [] for k in grupos}
    for perm in permissoes:
        for grupo, palavras in grupos.items():
            if any(p in perm.codename for p in palavras):
                resultado[grupo].append(perm)
                break
    return resultado

