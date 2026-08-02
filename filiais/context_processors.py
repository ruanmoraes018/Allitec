# context_processors.py
from django.contrib.auth.models import Permission
from notifications.models import Notification

def notificacoes(request):
    if request.user.is_authenticated:
        notificacoes = Notification.objects.filter(recipient=request.user, unread=True)
        return {'notificacoes': notificacoes}
    return {'notificacoes': []}