from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf.urls.static import static
from django.conf import settings
from django.http import FileResponse
import os

def favicon_view(request):
    file_path = os.path.join('/home/allitec/Allitec/static/img/favicon.ico')
    return FileResponse(open(file_path, 'rb'), content_type='image/x-icon')


urlpatterns = [
    path('admin/logout/', auth_views.LogoutView.as_view(next_page='/admin/login/?next=/admin/'), name='admin_logout'),
    path('admin/', admin.site.urls),
    path('', include ('filiais.urls')),
    path('pedidos/', include ('pedidos.urls')),
    path('marcas/', include ('marcas.urls')),
    path('formas_pgto/', include ('formas_pgto.urls')),
    path('tabelas_preco/', include ('tabelas_preco.urls')),
    path('tp_cobrancas/', include ('tipo_cobranca.urls')),
    path('regras_produto/', include ('regras_produto.urls')),
    path('empresas/', include ('empresas.urls')),
    path('unidades/', include ('unidades.urls')),
    # path('compras/', include ('compras.urls')),
    path('entradas/', include ('entradas.urls')),
    # path('conferencias/', include ('conferencias.urls')),
    path('mensalidades/', include ('mensalidades.urls')),
    path('contratos/', include ('contratos.urls')),
    path('clientes/', include ('clientes.urls')),
    path('fornecedores/', include ('fornecedores.urls')),
    path('orcamentos/', include ('orcamentos.urls')),
    path('produtos/', include ('produtos.urls')),
    path('tecnicos/', include ('tecnicos.urls')),
    path('bancos/', include ('bancos.urls')),
    path('grupos/', include ('grupos.urls')),
    path('bairros/', include ('bairros.urls')),
    path('cidades/', include ('cidades.urls')),
    path('estados/', include ('estados.urls')),
    path('usuarios/', include('contas.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('favicon.ico', favicon_view, name='favicon'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)