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
    path('ler_xml/', views.ler_xml_entrada, name='ler-xml-entrada'),
    path('criar_fornecedor_xml/', views.criar_fornecedor_por_xml, name='criar-fornecedor-xml'),
    path('criar_produto_xml/', views.criar_produto_por_xml, name='criar-produto-xml'),
    path('criar_produtos_em_massa/', views.criar_produtos_em_massa, name='criar-produtos-em-massa'),
]
