from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Q
from util.permissoes import verifica_permissao
from util.logs import registrar_log, gerar_alteracoes
from .models import __MODELO__
from .forms import __MODELO__Form

@verifica_permissao("__APP__.view___MODELO_MINUSCULO__")
@login_required
def lista___APP__(request):
    s = request.GET.get("s")
    tp = request.GET.get("tp")
    reg = request.GET.get("reg", "10")
    empresa = request.user.empresa
    itens = __MODELO__.objects.filter(empresa=empresa)
    if tp == "cod" and s:
        try:
            itens = itens.filter(codigo=s)
        except ValueError:
            itens = __MODELO__.objects.none()
    # Campo padrão para pesquisa textual.
    # Ajuste caso o modelo utilize outro campo.
    elif tp == "desc" and s:
        itens = itens.filter(descricao__icontains=s)
    itens = itens.order_by("codigo")
    if reg == "todos":
        num_pagina = itens.count() or 1
    else:
        try:
            num_pagina = int(reg)
            if num_pagina <= 0:
                num_pagina = 10
        except ValueError:
            num_pagina = 10
    paginator = Paginator(itens, num_pagina)
    page = request.GET.get("page")
    itens = paginator.get_page(page)
    return render(request, "__APP__/lista.html",{ "itens": itens,"s": s,"tp": tp,"reg": reg,},)

@login_required
def lista___APP___ajax(request):
    termo = request.GET.get("term") or request.GET.get("q") or ""
    empresa = request.user.empresa
    try:
        if termo.isdigit():
            busca = Q(codigo=termo) | Q(descricao__icontains=termo)
        else:
            busca = Q(descricao__icontains=termo)
        itens = __MODELO__.objects.filter(busca, empresa=empresa,)[:20]
        results = [{"id": item.codigo, "text": str(item),} for item in itens]
        return JsonResponse({"results": results})
    except Exception as e:
        return JsonResponse({"results": [], "error": str(e),})

@login_required
def add___MODELO_MINUSCULO__(request):
    if not request.user.has_perm("__APP__.add___MODELO_MINUSCULO__"):
        messages.info(request, "Você não tem permissão para adicionar __MODELO_PLURAL_MINUSCULO__.")
        return redirect("/__APP__/lista/")
    if request.method == "POST":
        form = __MODELO__Form(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            if hasattr(item, "empresa"):
                item.empresa = request.user.empresa
            item.save()
            registrar_log(
                request, "CRIAR", "__MODELO__", str(item),
                f"Adicionou: {item}", item.id, gerar_alteracoes(obj_novo=item),
            )
            messages.success(request, "Registro adicionado com sucesso!")
            return redirect(f"/__APP__/lista/?tp=cod&s={item.codigo}")
        error_messages = []
        for field in form:
            if field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) possui erro.")
        return render(request, "__APP__/add.html", {"form": form, "error_messages": error_messages,},)
    form = __MODELO__Form()
    return render(request, "__APP__/add.html",{"form": form,},)

@login_required
def att___MODELO_MINUSCULO__(request, codigo):
    empresa = request.user.empresa
    item = get_object_or_404(__MODELO__, codigo=codigo, empresa=empresa,)
    item_old = __MODELO__.objects.get(codigo=item.codigo, empresa=empresa,)
    if not request.user.has_perm("__APP__.change___MODELO_MINUSCULO__"):
        messages.info(request, "Você não tem permissão para editar __MODELO_PLURAL_MINUSCULO__.")
        return redirect("/__APP__/lista/")
    if request.method == "POST":
        form = __MODELO__Form(request.POST, instance=item,)
        if form.is_valid():
            item = form.save()
            registrar_log(
                request, "ALTERAR", "__MODELO__", str(item),
                f"Alterou: {item}", item.id, gerar_alteracoes(item_old, item),
            )
            messages.success(request, "Registro atualizado com sucesso!")
            next_url = (request.POST.get("next") or request.GET.get("next"))
            if next_url:
                return redirect(next_url)
            return redirect(f"/__APP__/lista/?tp=cod&s={item.codigo}")
        error_messages = []
        for field in form:
            if field.errors:
                error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) possui erro.")
        return render(request, "__APP__/att.html",{"form": form, "item": item, "error_messages": error_messages,},)
    form = __MODELO__Form(instance=item)
    return render(request, "__APP__/att.html",{ "form": form, "item": item,},)

@login_required
def del___MODELO_MINUSCULO__(request, codigo):
    if not request.user.has_perm("__APP__.delete___MODELO_MINUSCULO__"):
        messages.info(request, "Você não tem permissão para deletar __MODELO_PLURAL_MINUSCULO__.")
        return redirect("/__APP__/lista/")
    item = get_object_or_404(__MODELO__, codigo=codigo, empresa=request.user.empresa,)
    registrar_log(
        request, "EXCLUIR", "__MODELO__", str(item),
        f"Excluiu: {item}", item.id, gerar_alteracoes(obj_antigo=item),
    )
    item.delete()
    messages.success(request, "Registro excluído com sucesso!")
    return redirect("/__APP__/lista/")