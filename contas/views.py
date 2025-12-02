from filiais.forms import EmpresaLoginForm
from django.urls import reverse_lazy
from django.views import generic
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from filiais.models import Filial, Usuario
from django.shortcuts import render, redirect, get_object_or_404
from .forms import UsuarioCadastroForm
from django.contrib import messages
from django.core.paginator import Paginator
from util.permissoes import verifica_permissao
from datetime import datetime
from django.db.models.functions import Concat, Substr
from empresas.models import Empresa
from django.db.models import Q


@login_required
def checar_permissao(request):
    nome_perm = request.GET.get('perm')
    if not nome_perm:
        return JsonResponse({'erro': 'Permissão não informada'}, status=400)

    permitido = nome_perm in request.user.get_all_permissions()
    return JsonResponse({'permitido': permitido})

class Registro(generic.CreateView):
    form_class = EmpresaLoginForm
    success_url = reverse_lazy('login')
    template_name = 'registration/registro.html'

def buscar_empresa(request):
    id_empresa = request.GET.get("id_empresa")

    try:
        empresa = Empresa.objects.get(id=id_empresa, principal="Sim")
        if empresa.situacao == "Inativa":  # Ajuste conforme o nome real do campo
            return JsonResponse({"success": False, "warning": "ID de empresa sem contrato ativo!"})

        return JsonResponse({"success": True, "fantasia": empresa.fantasia})
    except Empresa.DoesNotExist:
        return JsonResponse({"success": False})

@verifica_permissao('filiais.view_usuario')
@login_required
def lista_usuarios(request):
    s = request.GET.get('s')               # texto de busca
    tp = request.GET.get('tp')             # tipo de busca (desc ou cod)
    f_s = request.GET.get('sit')           # situação: Ativa / Inativa
    dt_ini = request.GET.get('dt_ini')     # data inicial
    dt_fim = request.GET.get('dt_fim')     # data final
    p_dt = request.GET.get('p_dt')         # filtrar por data? Sim / Não
    reg = request.GET.get('reg', '10')     # registros por página

    filial_user = request.user.filial_user

    if filial_user is None:
        usuarios = Usuario.objects.none()
    else:
        filial_principal = filial_user if filial_user.principal else filial_user.vinculada_a

        filiais_ids = Filial.objects.filter(
            Q(id=filial_principal.id) | Q(vinculada_a=filial_principal)
        ).values_list('id', flat=True)

        usuarios = Usuario.objects.filter(
            filial_user__in=filiais_ids
        ).select_related("filial_user")


    if tp == 'desc' and s:
        usuarios = usuarios.filter(user__last_name__icontains=s).order_by('user__last_name')
    elif tp == 'cod' and s:
        usuarios = usuarios.filter(user__id__icontains=s).order_by('id')

    # Filtro por data de nascimento (ou qualquer outro campo de data adaptado)
    if p_dt == 'Sim' and dt_ini and dt_fim:
        try:
            dt_ini_dt = datetime.strptime(dt_ini, '%d/%m/%Y').date()
            dt_fim_dt = datetime.strptime(dt_fim, '%d/%m/%Y').date()

            usuarios = usuarios.filter(date_joined__range=(dt_ini_dt, dt_fim_dt))
        except ValueError:
            usuarios = Usuario.objects.none()
    # Adiciona a fantasia da filial ao contexto
    for usuario in usuarios:
        usuario.filial_fantasia = usuario.filial_user.fantasia if usuario.filial_user else "Sem filial vinculada"

    if f_s and f_s.lower() != 'todos':  # Adicionado verificação para 'todos'
        if f_s.lower() == 'true':
            is_active = True
        elif f_s.lower() == 'false':
            is_active = False
        else:
            is_active = None

        if is_active is not None:
            usuarios = usuarios.filter(is_active=is_active)

    # Paginação
    if reg == 'todos':
        num_pagina = usuarios.count() or 1
    else:
        try:
            num_pagina = int(reg)
        except ValueError:
            num_pagina = 10

    paginator = Paginator(usuarios, num_pagina)
    page = request.GET.get('page')
    usuarios = paginator.get_page(page)

    return render(request, 'usuarios/lista.html', {
        'usuarios': usuarios,
        's': s,
        'tp': tp,
        'dt_ini': dt_ini,
        'dt_fim': dt_fim,
        'p_dt': p_dt,
        'reg': reg
    })

from collections import defaultdict
from django.contrib.auth.models import Permission
from django.utils.text import slugify

def agrupar_permissoes_por_grupo(permissoes):
    grupos = defaultdict(list)
    for perm in permissoes:
        grupos[perm.content_type.app_label].append(perm)
    return grupos

@login_required
def add_usuario(request):
    if not request.user.has_perm('filiais.add_usuario'):
        messages.info(request, 'Você não tem permissão para adicionar usuários.')
        return redirect('/usuarios/lista/')

    usuario_logado = request.user
    filial = usuario_logado.filial

    if not filial:
        messages.error(request, 'Usuário não está vinculado a uma filial.')
        return redirect('/usuarios/lista/')

    qtd_permitida = usuario_logado.empresa.qtd_usuarios
    usuarios_ativos = Usuario.objects.filter(
        empresa=usuario_logado.empresa,
        is_active=True
    ).exclude(is_master=True).count()


    if usuarios_ativos > qtd_permitida:
        messages.warning(request, f'Limite de {qtd_permitida} usuário(s) ativos atingido para sua empresa.')
        return redirect('/usuarios/lista/')

    todas_permissoes = Permission.objects.all()
    permissoes_por_grupo = agrupar_permissoes_por_grupo(todas_permissoes)
    grupos_marcados = []

    if request.method == 'POST':
        form = UsuarioCadastroForm(request.POST, filial_user=filial)
        gerar_senha_lib = request.POST.get('gerar_senha_lib') == 'on'
        senha_liberacao = request.POST.get('senha_liberacao')

        if form.is_valid():
            novo_user = form.save(commit=False)
            novo_user.first_name = request.POST.get('first_name')
            novo_user.set_password(request.POST.get('password'))
            novo_user.empresa = usuario_logado.empresa

            novo_user.filial_user = request.POST.get('filial_user')
            novo_user.gerar_senha_lib = gerar_senha_lib
            novo_user.senha_liberacao = senha_liberacao
            novo_user.save()

            permissoes = form.cleaned_data.get('permissoes')
            if permissoes:
                novo_user.user_permissions.set(permissoes)

            messages.success(request, 'Usuário cadastrado com sucesso.')
            return redirect('/usuarios/lista/')
        else:
            messages.error(request, 'Erro ao cadastrar usuário.')

            permissoes_selecionadas = form.cleaned_data.get('permissoes', [])
            for grupo, permissoes in permissoes_por_grupo.items():
                if all(perm in permissoes_selecionadas for perm in permissoes):
                    grupos_marcados.append(slugify(grupo))
    else:
        form = UsuarioCadastroForm(filial_user=filial)

    context = {
        'form': form,
        'filial': filial,
        'permissoes_por_grupo': permissoes_por_grupo,
        'grupos_marcados': grupos_marcados,
    }
    return render(request, 'usuarios/add_usuario.html', context)


@login_required
def att_usuario(request, id):
    usuario = get_object_or_404(Usuario, id=id)

    if not request.user.has_perm('filiais.change_usuario'):
        messages.info(request, 'Você não tem permissão para editar usuários.')
        return redirect('/usuarios/lista/')

    filial = usuario.filial_user

    todas_permissoes = Permission.objects.all()
    permissoes_por_grupo = agrupar_permissoes_por_grupo(todas_permissoes)
    grupos_marcados = []

    if request.method == 'POST':
        form = UsuarioCadastroForm(request.POST, instance=usuario, filial_user=filial)
        gerar_senha_lib = request.POST.get('gerar_senha_lib') == 'on'
        senha_liberacao = request.POST.get('senha_liberacao')

        if form.is_valid():
            user = form.save(commit=False)
            user.first_name = request.POST.get('first_name')

            user.save()

            permissoes = form.cleaned_data.get('permissoes')
            if permissoes is not None:
                user.user_permissions.set(permissoes)

            usuario.gerar_senha_lib = gerar_senha_lib
            usuario.senha_liberacao = senha_liberacao
            usuario.save()

            messages.success(request, 'Usuário atualizado com sucesso.')
            return redirect('/usuarios/lista/')
        else:
            messages.error(request, 'Erro ao atualizar usuário.')

            permissoes_selecionadas = form.cleaned_data.get('permissoes', [])
            for grupo, permissoes in permissoes_por_grupo.items():
                if all(perm in permissoes_selecionadas for perm in permissoes):
                    grupos_marcados.append(slugify(grupo))
    else:
        permissao_ids = list(usuario.user_permissions.values_list('id', flat=True))
        form = UsuarioCadastroForm(
            instance=usuario,
            initial={'permissoes': permissao_ids},
            filial_user=filial
        )

        for grupo, permissoes in permissoes_por_grupo.items():
            if all(perm.id in permissao_ids for perm in permissoes):
                grupos_marcados.append(slugify(grupo))

    context = {
        'form': form,
        'usuario': usuario,
        'filial': filial,
        'permissoes_por_grupo': permissoes_por_grupo,
        'grupos_marcados': grupos_marcados,
    }
    return render(request, 'usuarios/att_usuario.html', context)

@login_required
def del_usuario(request, id):
    usuario = get_object_or_404(Usuario, id=id)

    if not request.user.has_perm('filiais.delete_usuario'):
        messages.info(request, 'Você não tem permissão para deletar usuários.')
        return redirect('/usuarios/lista/')

    if usuario.user.username.lower() == 'allitec':
        messages.error(request, 'Você não tem permissão para deletar este usuário.')
        return redirect('/usuarios/lista/')
    else:
        usuario.user.delete()
        usuario.delete()
        messages.success(request, 'Usuário excluído com sucesso.')
        return redirect('/usuarios/lista/')

