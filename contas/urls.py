from django.urls import path
from . import views
urlpatterns = [
    path('registro/', views.Registro.as_view(), name='registro'),
    path("buscar_empresa/", views.buscar_empresa, name="buscar_empresa"),
    path("lista/", views.lista_usuarios, name='lista-usuarios'),
    path("add/", views.add_usuario, name="add-usuario"),
    path("att/<int:id>/", views.att_usuario, name='att-usuario'),
    path("del/<int:id>/", views.del_usuario, name='del-usuario'),
    path('ajax/permissao/', views.checar_permissao, name='checar_permissao'),

]