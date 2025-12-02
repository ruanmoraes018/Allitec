from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_unidades, name='lista-unidades'),
    path("lista_ajax/", views.lista_unidades_ajax, name='lista_ajax_unidades'),
    path("add/", views.add_unidade, name='add-unidade'),
    path("att/<int:id>/", views.att_unidade, name='att-unidade'),
    path("del/<int:id>/", views.del_unidade, name='del-unidade'),
]