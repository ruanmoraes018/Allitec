from django.urls import path
from . import views
urlpatterns = [
    path("lista/", views.lista_orcamentos, name='lista-orcamentos'),
    # path("lista_ajax/", views.lista_produtos_ajax, name='lista_produtos_ajax'),
    path("add/", views.add_orcamento, name='add-orcamento'),
    path("att/<int:id>/", views.att_orcamento, name='att-orcamento'),
    path("clonar/<int:id>/", views.clonar_orcamento, name='clonar-orcamento'),
    path("del/<int:id>/", views.del_orcamento, name='del-orcamento'),
    path("pdf_orcamento/<int:id>/", views.pdf_orcamento_html, name='pdf-orcamento'),
    # PDF novo (HTML + Chrome)
    # path('pdf-html/<int:id>/', views.pdf_orcamento_html, name='pdf_orcamento_html'),
    path("pdf_contrato/<int:id>/", views.gerar_contrato_pdf, name='pdf-contrato'),
    path("contrato-html/<int:id>/", views.pdf_contrato_html, name='pdf-contrato-html'),
    path("pdf_cont_v2/<int:id>/", views.pdf_contrato_v2, name='pdf-cont-v2'),
    path('fat_orc/<int:id>/', views.faturar_orcamento, name='faturar-orcamento'),
    path('canc_orc/<int:id>/', views.cancelar_orcamento, name='cancelar-orcamento'),
    path('comprovante/<int:id>/', views.imprimir_comprovante, name='comprovante'),
    path('pdf_a4/<int:id>/', views.imprimir_comp_a4, name='pdf-a4'),
    path('enviar-solicitacao/', views.enviar_solicitacao, name='enviar_solicitacao'),
    path('verificar-solicitacao/<int:solicitacao_id>/', views.verificar_status_solicitacao, name='verificar_solicitacao'),
    path('responder-solicitacao/', views.responder_solicitacao, name='responder_solicitacao'),
    path('usuarios-com-permissao/', views.usuarios_com_permissao, name='usuarios_com_permissao'),
    path("alterar-status/", views.alterar_status_orcamento, name="alterar_status_orcamento"),
]
