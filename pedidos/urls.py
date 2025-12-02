from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_pedidos, name='lista-pedidos'),
    path("add/", views.add_pedido, name='add-pedido'),
    path("att/<int:id>/", views.att_pedido, name='att-pedido'),
    path("del/<int:id>/", views.del_pedido, name='del-pedido'),
    path('pedidos-produto/<int:produto_id>/', views.pedidos_por_produto, name='pedidos_por_produto'),
]