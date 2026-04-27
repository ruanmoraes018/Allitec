from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_contas_receber, name='lista-contas-receber'),
    path("lista_ajax/", views.lista_contas_receber_ajax, name='lista_ajax_contas_receber'),
    path('detalhes_ajax/<int:id>/', views.detalhes_conta_receber_ajax, name='detalhes_conta_receber_ajax'),
    path("add/", views.add_conta_receber, name='add-conta-receber'),
    path("att/<int:id>/", views.att_conta_receber, name='att-conta-receber'),
    path("del/<int:id>/", views.del_conta_receber, name='del-conta-receber'),
    path("pagar/<int:id>/", views.pagar_conta_receber, name="pagar-conta-receber"),
    path("estornar/<int:id>/", views.estornar_conta_receber, name="estornar-conta-receber"),
    path("<int:conta_id>/gerar-pagamento/", views.gerar_pix_conta_receber, name='gerar-recebimento-cr'),
    path('<int:conta_id>/status-pagamento/', views.status_pagamento_conta, name='status-pagamento-cr'),
]