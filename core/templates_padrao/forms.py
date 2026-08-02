from django import forms
from .models import __MODELO__

class __MODELO__Form(forms.ModelForm):

    class Meta:
        model = __MODELO__
        fields = "__all__"