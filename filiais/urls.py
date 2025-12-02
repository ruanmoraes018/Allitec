from django.urls import path
from . import views
urlpatterns = [
    path('', views.dashboard, name='inicio'),
    path("accounts/login/", views.login_filial, name="login"),
    path("accounts/login-superuser/", views.login_superusuario, name="login-superuser"),
    path('logout/', views.logout_view, name='logout-view'),
    path('logout-superuser/', views.logout_view_superuser, name='logout-view-superuser'),
    path("filiais/lista/", views.lista_filiais, name='lista-filiais'),
    path('ajax/filiais-vinculadas/', views.filiais_vinculadas_ajax, name='filiais_vinculadas_ajax'),
    path('filiais/lista_ajax/', views.lista_filiais_ajax, name='lista_filiais_ajax'),
    path("filiais/add/", views.add_filial, name='add-filial'),
    path('filiais/att/<int:id>/', views.att_filial, name='att-filial'),
    path('filiais/del/<int:id>/', views.del_filial, name='del-filial'),
    path('verificar-localizacao/', views.verificar_ou_criar_localizacao, name='verificar_localizacao'),
    path('ajax/notificacoes/', views.notificacoes_ajax, name='notificacoes_ajax'),
]
