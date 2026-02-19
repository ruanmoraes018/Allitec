from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_mensalidades, name='lista-mensalidades'),
    path("lista_ajax/", views.lista_mensalidades_ajax, name='lista_ajax_mensalidades'),
    path("add/", views.add_mensalidade, name='add-mensalidade'),
    path("att/<int:id>/", views.att_mensalidade, name='att-mensalidade'),
    path("del/<int:id>/", views.del_mensalidade, name='del-mensalidade'),
    path("baixar/<int:id>/", views.baixar_mensalidade, name="baixar-mensalidade"),
    path("estornar/<int:id>/", views.estornar_mensalidade, name="estornar-mensalidade"),
    path('webhook/mp/', views.webhook_mp, name='webhook_mp'),
    path('gerar-pix-lote/', views.gerar_pix_lote_view),
    path('pix/<str:id>/', views.visualizar_pix),
    path('status-pix/<str:id>/', views.status_pix),
    path('portal/', views.portal_pagamentos, name='portal_pagamentos'),
    path('login/', views.login_portal, name="login_portal"),
    path('logout/', views.logout_portal, name="logout_portal"),
]