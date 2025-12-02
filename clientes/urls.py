from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_clientes, name='lista-clientes'),
    path("lista_ajax/", views.lista_clientes_ajax, name='lista_clientes_ajax'),
    path("add/", views.add_cliente, name='add-cliente'),
    path("att/<int:id>/", views.att_cliente, name='att-cliente'),
    path("del/<int:id>/", views.del_cliente, name='del-cliente'),
    # path('mudar_situacao_membro/<int:id>', views.mudar_situacao_membro, name='mudar-situacao-membro'),
]
