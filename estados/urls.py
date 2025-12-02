from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_estados, name='lista-estados'),
    path("lista_ajax/", views.lista_estados_ajax, name='lista_ajax_estados'),
    path("add/", views.add_estado, name='add-estado'),
    path("att/<int:id>/", views.att_estado, name='att-estado'),
    path("del/<int:id>/", views.del_estado, name='del-estado'),
]