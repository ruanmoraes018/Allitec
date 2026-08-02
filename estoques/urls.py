from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_estoques, name='lista-estoques'),
    path("lista_ajax/", views.lista_estoques_ajax, name='lista_ajax_estoques'),
    path("add/", views.add_estoque, name='add-estoque'),
    path("att/<int:codigo>/", views.att_estoque, name='att-estoque'),
    path("del/<int:codigo>/", views.del_estoque, name='del-estoque'),
]