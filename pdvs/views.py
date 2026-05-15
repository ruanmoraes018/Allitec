from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import PDV
from .forms import PDVForm
import unicodedata
from django.http import JsonResponse
from util.permissoes import verifica_permissao
from django.db.models import Q
from filiais.models import Filial

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

@verifica_permissao('pdvs.view_pdv')
@login_required
def lista_pdvs(request):
    s = request.GET.get('s')
    tp = request.GET.get('tp')
    sit = request.GET.get('sit')
    fil = request.GET.get('fil')
    reg = request.GET.get('reg', '10')
    empresa = request.user.empresa
    pdvs = PDV.objects.filter(vinc_emp=empresa)
    if tp == 'desc' and s:
        norm_s = remove_accents(s).lower()
        pdvs = pdvs.filter(nome__icontains=norm_s).order_by('nome')
    elif tp == 'cod' and s:
        try:
            pdvs = pdvs.filter(id__iexact=s).order_by('nome')
        except ValueError:
            pdvs = PDV.objects.none()
    if sit and sit != 'Todos': pdvs = pdvs.filter(situacao=sit)
    if fil: pdvs = pdvs.filter(vinc_fil_id=fil)
    filiais = Filial.objects.filter(vinc_emp=request.user.empresa)
    if reg == 'todos':
        num_pagina = pdvs.count() or 1
    else:
        try:
            num_pagina = int(reg) if int(reg) > 0 else 1
        except ValueError:
            num_pagina = 10  # Valor padrão

    paginator = Paginator(pdvs, num_pagina)
    page = request.GET.get('page')
    pdvs = paginator.get_page(page)

    return render(request, 'pdvs/lista.html', {
        'pdvs': pdvs,
        'filiais': filiais,
        'sit': sit,
        's': s,
        'tp': tp,
        'reg': reg,
    })

@login_required
def lista_pdvs_ajax(request):
    termo_busca = request.GET.get('term') or request.GET.get('q') or ''
    empresa = request.user.empresa
    try:
        if termo_busca.isdigit():
            condicao_busca = Q(nome__icontains=termo_busca) | Q(id=termo_busca)
        else:
            condicao_busca = Q(nome__icontains=termo_busca)
        pdvs = PDV.objects.filter(condicao_busca & Q(vinc_emp=empresa))[:20]
        results = [{'id': p.id, 'text': f"{p.nome.upper()}"} for p in pdvs]
        return JsonResponse({'results': results})
    except Exception as e:
        print(f"Erro na busca AJAX: {e}")
        return JsonResponse({'results': [], 'error': str(e)})
    
@login_required
def add_pdv(request):
    if not request.user.has_perm('pdvs.add_pdv'):
        messages.info(request, 'Você não tem permissão para adicionar PDVs.')
        return redirect('/pdvs/lista/')
    if request.method == 'POST':
        form = PDVForm(request.POST, empresa=request.user.empresa, user=request.user)
        if form.is_valid():
            b = form.save(commit=False)
            b.vinc_emp = request.user.empresa
            b.save()
            messages.success(request, 'PDV adicionado com sucesso!')
            bank = str(b.id)
            return redirect('/pdvs/lista/?tp=cod&s=' + bank)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'pdvs/add.html', {'form': form, 'error_messages': error_messages})
    else: form = PDVForm(empresa=request.user.empresa, user=request.user)
    return render(request, 'pdvs/add.html', {'form': form})

@login_required
def att_pdv(request, id):
    b = get_object_or_404(PDV, pk=id, vinc_emp=request.user.empresa)
    form = PDVForm(instance=b, empresa=request.user.empresa, user=request.user)
    if not request.user.has_perm('pdvs.change_pdv'):
        messages.info(request, 'Você não tem permissão para editar PDVs.')
        return redirect('/pdvs/lista/')
    if request.method == 'POST':
        form = PDVForm(request.POST, instance=b, empresa=request.user.empresa, user=request.user)
        if form.is_valid():
            b.save()
            next_url = request.POST.get('next') or request.GET.get('next')
            bank = str(b.id)
            messages.success(request, 'PDV atualizado com sucesso!')
            if next_url:
                return redirect(next_url)
            else:
                return redirect('/pdvs/lista/?tp=cod&s=' + bank)
        else:
            error_messages = []
            for field in form:
                if field.errors:
                    for error in field.errors:
                        error_messages.append(f"<i class='fa-solid fa-xmark'></i> Campo ({field.label}) é obrigatório!")
            return render(request, 'pdvs/att.html', {'form': form, 'b': b, 'error_messages': error_messages})
    else:
        return render(request, 'pdvs/att.html', {'form': form, 'b': b})

@login_required
def del_pdv(request, id):
    if not request.user.has_perm('pdvs.delete_pdv'):
        messages.info(request, 'Você não tem permissão para deletar PDVs.')
        return redirect('/pdvs/lista/')
    b = get_object_or_404(PDV, pk=id, vinc_emp=request.user.empresa)
    if b.caixamovimento_set.exists():
        messages.error(request, 'Não é possível deletar este PDV porque existem movimentos associados a ele.')
        return redirect('/pdvs/lista/')
    else:   
        b.delete()
        messages.success(request, 'PDV deletado com sucesso!')
        return redirect('/pdvs/lista/')