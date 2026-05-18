from django.urls import path
from .views import *
urlpatterns = [
    path("lista_ajax/", lista_tecnicos_ajax, name="lista-tecnicos-ajax"),
    path("lista/", lista_tecnicos, name='lista-tecnicos'),
    path("add/", add_tecnico, name="add-tecnico"),
    path("att/<int:codigo>/", att_tecnico, name='att-tecnico'),
    path("del/<int:codigo>/", del_tecnico, name='del-tecnico'),
]