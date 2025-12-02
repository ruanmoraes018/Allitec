from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_fornecedores, name='lista-fornecedores'),
    path("lista_ajax/", views.lista_fornecedores_ajax, name='lista_fornecedores_ajax'),
    path("add/", views.add_fornecedor, name='add-fornecedor'),
    path("att/<int:id>/", views.att_fornecedor, name='att-fornecedor'),
    path("del/<int:id>/", views.del_fornecedor, name='del-fornecedor'),
    # path('mudar_situacao_membro/<int:id>', views.mudar_situacao_membro, name='mudar-situacao-membro'),
]
