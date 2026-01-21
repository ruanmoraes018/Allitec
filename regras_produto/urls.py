from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_regras, name='lista-regras'),
    path("lista_ajax/", views.lista_regras_ajax, name='lista-ajax'),
    path("add/", views.add_regra, name='add-regra'),
    path("att/<int:id>/", views.att_regra, name='att-regra'),
    path("del/<int:id>/", views.del_regra, name='del-regra'),
    path('js/', views.regras_js, name='regras_js'),
]