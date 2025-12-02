from django.urls import path
from . import views

urlpatterns = [
    path("lista/", views.lista_empresas, name='lista-empresas'),
    path("lista_ajax/", views.lista_empresas_ajax, name='lista-empresas-ajax'),
    path("add/", views.add_empresa, name='add-empresa'),
    path("att/<int:id>/", views.att_empresa, name='att-empresa'),
    path("del/<int:id>/", views.del_empresa, name='del-empresa'),
]
