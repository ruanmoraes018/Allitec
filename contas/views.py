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
from collections import defaultdict
from django.contrib.auth.models import Permission
from django.utils.text import slugify

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

@login_required
@verifica_permissao('filiais.view_usuario')
def lista_usuarios(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    f_s = request.GET.get('sit')
    dt_ini = request.GET.get('dt_ini')
    dt_fim = request.GET.get('dt_fim')
    p_dt = request.GET.get('p_dt')
    reg = request.GET.get('reg', '10')

    empresa = request.user.empresa
    filial_user = request.user.filial_user

    if filial_user is None:
        usuarios = Usuario.objects.none()

    else:
        filial_principal = filial_user if filial_user.principal else filial_user.vinculada_a

        filiais_ids = Filial.objects.filter(
            vinc_emp=empresa
        ).filter(
            Q(id=filial_principal.id) | Q(vinculada_a=filial_principal)
        ).values_list('id', flat=True)

        usuarios = Usuario.objects.filter(
            empresa=empresa,
            filial_user_id__in=filiais_ids
        ).select_related('filial_user')

    # Busca por descrição
    if tp == 'desc' and s:
        usuarios = usuarios.filter(first_name__icontains=s).order_by('first_name')

    # Busca por código
    elif tp == 'cod' and s:
        usuarios = usuarios.filter(id__icontains=s).order_by('id')

    # Filtro por data
    if p_dt == 'Sim' and dt_ini and dt_fim:
        try:
            dt_ini_dt = datetime.strptime(dt_ini, '%d/%m/%Y').date()
            dt_fim_dt = datetime.strptime(dt_fim, '%d/%m/%Y').date()
            usuarios = usuarios.filter(date_joined__range=(dt_ini_dt, dt_fim_dt))
        except ValueError:
            usuarios = Usuario.objects.none()

    # Situação
    if f_s and f_s.lower() != 'todos':
        if f_s.lower() == 'true':
            usuarios = usuarios.filter(is_active=True)
        elif f_s.lower() == 'false':
            usuarios = usuarios.filter(is_active=False)

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
    filial = usuario_logado.filial_user
    if not filial:
        messages.error(request, 'Usuário não está vinculado a uma filial.')
        return redirect('/usuarios/lista/')
    qtd_permitida = usuario_logado.empresa.qtd_usuarios
    usuarios_ativos = Usuario.objects.filter(empresa=usuario_logado.empresa, is_active=True).exclude(is_master=True).count()
    if usuarios_ativos >= qtd_permitida:
        messages.warning(request, f'Limite de {qtd_permitida} usuário(s) ativos atingido para sua empresa.')
        return redirect('/usuarios/lista/')
    todas_permissoes = Permission.objects.all()
    permissoes_por_grupo = agrupar_permissoes_por_grupo(todas_permissoes)
    grupos_marcados = []
    if request.method == 'POST':
        form = UsuarioCadastroForm(request.POST, empresa=request.user.empresa)
        gerar_senha_lib = request.POST.get('gerar_senha_lib') == 'on'
        senha_liberacao = request.POST.get('senha_liberacao')
        if form.is_valid():
            novo_user = form.save(commit=False)
            novo_user.first_name = request.POST.get('first_name')
            novo_user.set_password(request.POST.get('password'))
            novo_user.empresa = usuario_logado.empresa
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
        form = UsuarioCadastroForm(empresa=request.user.empresa)
    context = {'form': form, 'filial': filial, 'permissoes_por_grupo': permissoes_por_grupo, 'grupos_marcados': grupos_marcados}
    return render(request, 'usuarios/add_usuario.html', context)

@login_required
def att_usuario(request, id):
    usuario = get_object_or_404(Usuario, pk=id, empresa=request.user.empresa)
    if not request.user.has_perm('filiais.change_usuario'):
        messages.info(request, 'Você não tem permissão para editar usuários.')
        return redirect('/usuarios/lista/')
    filial = usuario.filial_user
    todas_permissoes = Permission.objects.all()
    permissoes_por_grupo = agrupar_permissoes_por_grupo(todas_permissoes)
    grupos_marcados = []
    if request.method == 'POST':
        form = UsuarioCadastroForm(request.POST, instance=usuario, empresa=request.user.empresa)
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
            next_url = request.POST.get('next') or request.GET.get('next')
            messages.success(request, 'Usuário atualizado com sucesso.')
            if next_url:
                return redirect(next_url)
            else:
                return redirect(f'/usuarios/lista/?tp=cod&s={usuario.id}')
        else:
            messages.error(request, 'Erro ao atualizar usuário.')
            permissoes_selecionadas = form.cleaned_data.get('permissoes', [])
            for grupo, permissoes in permissoes_por_grupo.items():
                if all(perm in permissoes_selecionadas for perm in permissoes):
                    grupos_marcados.append(slugify(grupo))
    else:
        permissao_ids = list(usuario.user_permissions.values_list('id', flat=True))
        form = UsuarioCadastroForm(instance=usuario, initial={'permissoes': permissao_ids}, empresa=request.user.empresa)
        for grupo, permissoes in permissoes_por_grupo.items():
            if all(perm.id in permissao_ids for perm in permissoes):
                grupos_marcados.append(slugify(grupo))
    context = {'form': form, 'usuario': usuario, 'filial': filial, 'permissoes_por_grupo': permissoes_por_grupo, 'grupos_marcados': grupos_marcados}
    return render(request, 'usuarios/att_usuario.html', context)

@login_required
def del_usuario(request, id):
    usuario = get_object_or_404(Usuario, pk=id, empresa=request.user.empresa)
    if not request.user.has_perm('filiais.delete_usuario'):
        messages.info(request, 'Você não tem permissão para deletar usuários.')
        return redirect('/usuarios/lista/')
    if usuario.username.lower() == 'allitec':
        messages.error(request, 'Você não tem permissão para deletar este usuário.')
        return redirect('/usuarios/lista/')
    else:
        usuario.delete()
        messages.success(request, 'Usuário excluído com sucesso.')
        return redirect('/usuarios/lista/')