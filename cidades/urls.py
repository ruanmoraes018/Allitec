from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_cidades, name='lista-cidades'),
    path("lista_ajax/", views.lista_cidades_ajax, name='lista_ajax_cidades'),
    path("add/", views.add_cidade, name='add-cidade'),
    path("att/<int:codigo>/", views.att_cidade, name='att-cidade'),
    path("del/<int:codigo>/", views.del_cidade, name='del-cidade'),
]