from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_lancamentos, name='lista-lancamentos'),
    path("lista_ajax/", views.lista_lancamentos_ajax, name='lista-ajax'),
    path("add/", views.add_lancamento, name='add-lancamento'),
    path("att/<int:codigo>/", views.att_lancamento, name='att-lancamento'),
    path("del/<int:codigo>/", views.del_lancamento, name='del-lancamento'),
    path('caixa/<int:caixa_id>/', views.tela_caixa, name='tela-caixa'),
    path('caixa/finalizar/', views.finalizar_venda, name='finalizar-venda'),
    path('caixa/gerar-pagamento/', views.gerar_pagamento_caixa, name='gerar-pagamento'),
    # path('caixa/fechar/<int:caixa_id>/', views.fechar_caixa, name='fechar-caixa'),
    path('caixa/status-pagamento/', views.status_pagamento_caixa, name='status-pagamento-caixa'),
    path('caixa/movimentos/<int:caixa_id>/', views.movimentos_caixa, name='movimentos-caixa'),
]