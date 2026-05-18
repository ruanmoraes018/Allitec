from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_bancos, name='lista-bancos'),
    path("lista_ajax/", views.lista_bancos_ajax, name='lista_bancos_ajax'),
    path("add/", views.add_banco, name='add-banco'),
    path("att/<int:codigo>/", views.att_banco, name='att-banco'),
    path("del/<int:codigo>/", views.del_banco, name='del-banco'),
]