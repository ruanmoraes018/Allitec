from django.urls import path
from . import views_gr
urlpatterns = [
    path("lista/", views_gr.lista_grupos_regras, name='lista-grupos-regras'),
    path("lista_ajax/", views_gr.lista_grupos_regras_ajax, name='lista_ajax_grupos_regras'),
    path("add/", views_gr.add_grupo_regras, name='add-grupo-regras'),
    path("att/<int:cod_local>/", views_gr.att_grupo_regras, name='att-grupo-regras'),
    path("del/<int:cod_local>/", views_gr.del_grupo_regras, name='del-grupo-regras'),
]