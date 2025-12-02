from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_formas_pgto, name='lista-formas_pgto'),
    path("lista_ajax/", views.lista_formas_pgto_ajax, name='lista_ajax_formas_pgto'),
    path("get/", views.get_forma_pgto, name="get_forma_pgto"),
    path("add/", views.add_formas_pgto, name='add-formas_pgto'),
    path("att/<int:id>/", views.att_formas_pgto, name='att-formas_pgto'),
    path("del/<int:id>/", views.del_formas_pgto, name='del-formas_pgto'),
]