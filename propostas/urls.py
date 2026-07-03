from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_propostas, name='lista-propostas'),
    path("confirmar/<int:id>/", views.mudar_situacao, name='confirmar-proposta'),
    path("add/", views.adicionar_proposta, name='add-proposta'),
    path("att/<int:id>/", views.atualizar_proposta, name='att-proposta'),
    path("del/<int:id>/", views.deletar_proposta, name='del-proposta'),
    path('pdf/<int:id>/', views.pdf_prop_html, name='gerar_proposta'),
]
