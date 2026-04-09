from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_produtos, name='lista-produtos'),
    path('produtos/att-lote/', views.att_prod_lote, name='att-prod-lote'),
    path('produtos/att-tb-preco-lote/', views.att_preco_lote, name="att-tb-preco-lote"),
    path('att-tb-preco-lt/', views.att_tb_preco_lote, name="att_tb_preco_lote"),
    path("lista_ajax/", views.buscar_produtos, name='buscar_produtos'),
    path("lista_ajax1/", views.lista_produtos_ajax, name='lista_produtos_ajax'),
    path("lista_ajax_ent/", views.buscar_produtos_ent, name='buscar_produtos_ent'),
    path("add/", views.add_produto, name='add-produto'),
    path("att/<int:id>/", views.att_produto, name='att-produto'),
    path("del/<int:id>/", views.del_produto, name='del-produto'),
    path("clonar/<int:id>/", views.clonar_produto, name='clonar-produto'),
    path('ajax/salvar-tabelas/', views.salvar_tabelas_produto_ajax, name='salvar_tabelas_produto_ajax'),
    path('ajax/buscar-tabelas/', views.buscar_tabelas_produto_ajax, name='buscar_tabelas_produto_ajax'),
]