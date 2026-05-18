from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_fornecedores, name='lista-fornecedores'),
    path("lista_ajax/", views.lista_fornecedores_ajax, name='lista_fornecedores_ajax'),
    path("add/", views.add_fornecedor, name='add-fornecedor'),
    path("att/<int:codigo>/", views.att_fornecedor, name='att-fornecedor'),
    path("del/<int:codigo>/", views.del_fornecedor, name='del-fornecedor'),
    # path('mudar_situacao_membro/<int:codigo>', views.mudar_situacao_membro, name='mudar-situacao-membro'),
]
