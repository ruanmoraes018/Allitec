from django.contrib import messages
from django.shortcuts import redirect
from functools import wraps

def verifica_permissao(permissao_codename):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.has_perm(permissao_codename):
                try:
                    # permissao_codename no formato: 'app_label.action_model'
                    _, action_model = permissao_codename.split('.')
                    acao, model = action_model.split('_', 1)  # 'view_empresa' → 'view', 'empresa'
                    model_nome = model.replace('_', ' ').capitalize()
                    messages.info(
                        request,
                        f'Seu usuário não pode acessar a página de {model_nome}.'
                    )
                except Exception:
                    messages.info(
                        request,
                        'Você não tem permissão para acessar esta página.'
                    )
                return redirect('inicio')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def verifica_alguma_permissao(*permissoes_codenames):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not any(request.user.has_perm(perm) for perm in permissoes_codenames):
                messages.warning(
                    request,
                    'Usuário não autorizado para realizar esta função.'
                )
                return redirect('inicio')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator