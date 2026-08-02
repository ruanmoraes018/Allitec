from django.urls import path
from . import views

urlpatterns = [
    path("lista/", views.lista___APP__, name='lista-__APP__'),
    path("lista_ajax/", views.lista___APP___ajax, name='lista_ajax___APP__'),
    path("add/", views.add___MODELO_MINUSCULO__, name='add-__MODELO_MINUSCULO__'),
    path("att/<int:codigo>/", views.att___MODELO_MINUSCULO__, name='att-__MODELO_MINUSCULO__'),
    path("del/<int:codigo>/", views.del___MODELO_MINUSCULO__, name='del-__MODELO_MINUSCULO__'),
]