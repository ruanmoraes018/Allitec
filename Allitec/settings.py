import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-q+la1=z6y43yf-+j=c+3cf2scm_6lw6l)lz0y8lwb^5zv3i35z'
DEBUG = True
ALLOWED_HOSTS = ['*', 'allitec.pythonanywhere.com', '127.0.0.1']
CSRF_TRUSTED_ORIGINS = ['https://allitec.pythonanywhere.com']
INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions',
    'django.contrib.messages', 'django.contrib.staticfiles', 'core', 'pedidos', 'tabelas_preco', 'vendedores',
    'regras_produto', 'marcas', 'formas_pgto', 'tipo_cobranca', 'lancpdvs', 'pdvs', 'contas_pagar',
    'filiais', 'compras', 'entradas', 'conferencias', 'relatorios', 'propostas',
    'unidades', 'clientes', 'fornecedores', 'produtos', 'estoques', 'informacoes',
    'orcamentos', 'tecnicos', 'bancos', 'grupos', 'django.contrib.humanize',
    'empresas', 'bairros', 'cidades', 'estados', 'contas_receber',
    'notifications', 'mensalidades', 'contratos', 'crispy_forms', 'crispy_bootstrap5',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware', 'core.middleware.bloqueio.BloqueioInadimplenciaMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'Allitec.urls'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [os.path.join(BASE_DIR, 'templates')], 'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug', 'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages', 'filiais.context_processors.notificacoes', 'core.context_processors.financeiro_status',
            ],
        },
    },
]
WSGI_APPLICATION = 'Allitec.wsgi.application'
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.mysql",
#         "NAME": "allitec$erp",
#         "USER": "allitec",
#         "PASSWORD": "MinhaSenha123",
#         "HOST": "allitec.mysql.pythonanywhere-services.com",
#         "PORT": "3306",
#         "OPTIONS": {
#             "charset": "utf8mb4",
#             "init_command": "SET NAMES utf8mb4",
#         },
#     }
# }
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql", "NAME": "erp", "USER": "root", "PASSWORD": "senha", "HOST": "localhost", "PORT": "3306",
        "OPTIONS": {"charset": "utf8mb4", "init_command": "SET NAMES utf8mb4",},
    }
}
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',}, {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',}, {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]
AUTH_USER_MODEL = "filiais.Usuario"
AUTHENTICATION_BACKENDS = ['filiais.auth_backends.FilialBackend', 'contas.auth_backends.EmpresaCaseInsensitiveBackend',]
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Belem'  # ou America/Sao_Paulo
USE_TZ = True
USE_I18N = True
DATE_INPUT_FORMATS = ['%d/%m/%Y']
DATETIME_INPUT_FORMATS = ['%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M',]
USE_L10N = True
STATIC_URL = 'static/'
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"
MERCADOPAGO_ACCESS_TOKEN = "APP_USR-6431804173181676-062318-93e7cb60c5b3ffc2841b0e39114e84c4-235713412"
MEU_DANFE_API_KEY = '20bb8111-972e-4f4b-b46e-30488274912b'
MEU_DANFE_URL = 'https://api.meudanfe.com.br/v2/fd/convert/xml-to-da'
CSRF_TRUSTED_ORIGINS = ["https://allitec.pythonanywhere.com"]
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGOUT_REDIRECT_URL = 'https://allitec.pythonanywhere.com/admin/login/?next=/admin/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/contas/logout/'
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
STATIC_ROOT = BASE_DIR / 'staticfiles'
DJANGO_NOTIFICATIONS_CONFIG = {'USE_JSONFIELD': True,}
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000