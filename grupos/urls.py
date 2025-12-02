from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_grupos, name='lista-grupos'),
    path("lista_ajax/", views.lista_grupos_ajax, name='lista_ajax_grupos'),
    path("add/", views.add_grupo, name='add-grupo'),
    path("att/<int:id>/", views.att_grupo, name='att-grupo'),
    path("del/<int:id>/", views.del_grupo, name='del-grupo'),
]