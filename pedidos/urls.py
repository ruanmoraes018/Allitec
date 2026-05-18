from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_pedidos, name='lista-pedidos'),
    path('detalhes_ajax/<int:codigo>/', views.detalhes_pedido_ajax, name='detalhes_pedido_ajax'),
    path("add/", views.add_pedido, name='add-pedido'),
    path("att/<int:codigo>/", views.att_pedido, name='att-pedido'),
    path("clonar/<int:codigo>/", views.clonar_pedido, name='clonar-pedido'),
    path("del/<int:codigo>/", views.del_pedido, name='del-pedido'),
    path("faturar/<int:codigo>/", views.faturar_pedido, name='faturar-pedido'),
    path("cancelar/<int:codigo>/", views.cancelar_pedido, name='cancelar-pedido'),
    path("<int:pedido_id>/gerar-pagamento/", views.gerar_pagamento_pedido, name='gerar-pagamentos'),
    path('<int:pedido_id>/status-pagamento/', views.status_pagamento_pedido, name='status-pagamento-pedido'),
    path('<int:pedido_id>/recuperar-pagamento/', views.recuperar_pix_pendente, name='recuperar-pix-pendente'),
    path('pedidos-produto/<int:produto_id>/', views.pedidos_por_produto, name='pedidos_por_produto'),
    path('cupom/<int:codigo>/', views.imprimir_cupom_pedido, name='cupom_pedido'),
]