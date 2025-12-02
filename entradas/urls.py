from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_entradas, name='lista-entradas'),
    # path("lista_ajax/", views.lista_produtos_ajax, name='lista_produtos_ajax'),
    path("add/", views.add_entrada, name='add-entrada'),
    path("att/<int:id>/", views.att_entrada, name='att-entrada'),
    path("del/<int:id>/", views.del_entrada, name='del-entrada'),
    path("efetivar/<int:id>/", views.efetivar_entrada, name='efetivar-entrada'),
    path("cancelar/<int:id>/", views.cancelar_entrada, name='cancelar-entrada'),
    path('entradas-produto/<int:produto_id>/', views.entradas_por_produto, name='entradas_por_produto'),
]
