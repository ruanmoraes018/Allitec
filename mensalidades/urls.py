from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_mensalidades, name='lista-mensalidades'),
    path("lista_ajax/", views.lista_mensalidades_ajax, name='lista_ajax_mensalidades'),
    path("add/", views.add_mensalidade, name='add-mensalidade'),
    path("att/<int:id>/", views.att_mensalidade, name='att-mensalidade'),
    path("del/<int:id>/", views.del_mensalidade, name='del-mensalidade'),
]