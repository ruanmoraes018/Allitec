from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_bairros, name='lista-bairros'),
    path("lista_ajax/", views.lista_bairros_ajax, name='lista_ajax_bairros'),
    path("add/", views.add_bairro, name='add-bairro'),
    path("att/<int:id>/", views.att_bairro, name='att-bairro'),
    path("del/<int:id>/", views.del_bairro, name='del-bairro'),
]