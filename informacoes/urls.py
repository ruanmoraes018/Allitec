from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_informacoes, name='lista-informacoes'),
    path("lista_ajax/", views.lista_informacoes_ajax, name='lista_ajax_informacoes'),
    path("add/", views.add_informacao, name='add-informacao'),
    path("att/<int:codigo>/", views.att_informacao, name='att-informacao'),
    path("del/<int:codigo>/", views.del_informacao, name='del-informacao'),
]