from django.urls import path
from . import views

urlpatterns = [
    path("lista/", views.lista_contas_pagar, name='lista-contas_pagar'),
    path("lista_ajax/", views.lista_contas_pagar_ajax, name='lista_ajax_contas_pagar'),
    path("add/", views.add_conta_pagar, name='add-conta_pagar'),
    path("att/<int:codigo>/", views.att_conta_pagar, name='att-conta_pagar'),
    path("del/<int:codigo>/", views.del_conta_pagar, name='del-conta_pagar'),
    path('detalhes_ajax/<int:codigo>/', views.detalhes_conta_pagar_ajax, name='detalhes_conta_pagar_ajax'),
    path("pagar/<int:codigo>/", views.pagar_conta_pagar, name="pagar-conta-pagar"),
    path("estornar/<int:codigo>/", views.estornar_conta_pagar, name="estornar-conta-pagar"),
    path('recibo/<int:codigo>/', views.recibo_cp, name='recibo_cp'),
]