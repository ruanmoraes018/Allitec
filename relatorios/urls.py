from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_relatorios, name='lista-relatorios'),
    path("rel.pedidos/", views.relatorio_pedidos, name='relatorio_pedidos'),
    path("rel.vendas.produtos/", views.relatorio_produtos_vendidos, name='relatorio_vendas_produto'),
]