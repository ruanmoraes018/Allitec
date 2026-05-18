from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_vendedores, name='lista-vendedores'),
    path("lista_ajax/", views.lista_vendedores_ajax, name='lista_vendedores_ajax'),
    path("add/", views.add_vendedor, name='add-vendedor'),
    path("att/<int:codigo>/", views.att_vendedor, name='att-vendedor'),
    path("del/<int:codigo>/", views.del_vendedor, name='del-vendedor'),
    # path('mudar_situacao_membro/<int:codigo>', views.mudar_situacao_membro, name='mudar-situacao-membro'),
]
