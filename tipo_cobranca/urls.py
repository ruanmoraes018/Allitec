from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_tp_cobrancas, name='lista-tp_cobrancas'),
    path("lista_ajax/", views.lista_tp_cobrancas_ajax, name='lista_ajax_tp_cobrancas'),
    path("add/", views.add_tp_cobranca, name='add-tp_cobranca'),
    path("att/<int:id>/", views.att_tp_cobranca, name='att-tp_cobranca'),
    path("del/<int:id>/", views.del_tp_cobranca, name='del-tp_cobranca'),
]