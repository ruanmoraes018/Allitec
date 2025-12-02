from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_marcas, name='lista-marcas'),
    path("lista_ajax/", views.lista_marcas_ajax, name='lista_ajax_marcas'),
    path("add/", views.add_marca, name='add-marca'),
    path("att/<int:id>/", views.att_marca, name='att-marca'),
    path("del/<int:id>/", views.del_marca, name='del-marca'),
]