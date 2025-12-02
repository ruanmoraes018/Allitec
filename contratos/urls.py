from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_contratos, name='lista-contratos'),
    path("lista_ajax/", views.lista_contratos_ajax, name='lista_ajax_contratos'),
    path("add/", views.add_contrato, name='add-contrato'),
    path("att/<int:id>/", views.att_contrato, name='att-contrato'),
    path("del/<int:id>/", views.del_contrato, name='del-contrato'),
    path("aprovar-contrato/<int:id>/", views.aprovar_contrato, name='aprovar-contrato'),
]