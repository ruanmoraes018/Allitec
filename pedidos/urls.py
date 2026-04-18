from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_pedidos, name='lista-pedidos'),
    path("add/", views.add_pedido, name='add-pedido'),
    path("att/<int:id>/", views.att_pedido, name='att-pedido'),
    path("clonar/<int:id>/", views.clonar_pedido, name='clonar-pedido'),
    path("del/<int:id>/", views.del_pedido, name='del-pedido'),
    path("faturar/<int:id>/", views.faturar_pedido, name='faturar-pedido'),
    path("cancelar/<int:id>/", views.cancelar_pedido, name='cancelar-pedido'),
    path("<int:pedido_id>/gerar-pagamento/", views.gerar_pagamento_pedido, name='gerar-pagamentos'),
    path("<int:pedido_id>/status-pagamento/", views.status_pagamento_pedido, name='status-pagamentos'),
    path("<int:id>/gerar-pix/", views.gerar_pix_pedido, name='gerar-pix'),
    path('pedidos-produto/<int:produto_id>/', views.pedidos_por_produto, name='pedidos_por_produto'),
]