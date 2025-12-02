from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_tabelas_preco, name='lista-tabelas_preco'),
    path("lista_ajax/", views.lista_tabelas_preco_ajax, name='lista_ajax_tabelas_preco'),
    path("get/", views.get_tabela_preco, name="get_tabela_preco"),
    path("add/", views.add_tabelas_preco, name='add-tabelas_preco'),
    path("att/<int:id>/", views.att_tabelas_preco, name='att-tabelas_preco'),
    path("del/<int:id>/", views.del_tabelas_preco, name='del-tabelas_preco'),
]