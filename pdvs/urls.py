from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_pdvs, name='lista-pdvs'),
    path("lista_ajax/", views.lista_pdvs_ajax, name='lista-ajax'),
    path("add/", views.add_pdv, name='add-pdv'),
    path("att/<int:id>/", views.att_pdv, name='att-pdv'),
    path("del/<int:id>/", views.del_pdv, name='del-pdv'),
]