# gather/organizers/forms.py
from django import forms

from .models import Organizer


class OrganizerProfileForm(forms.ModelForm):
    """Formulaire self-service : club, poste et dates de mandat restent
    réservés à l'admin (données institutionnelles)."""

    class Meta:
        model = Organizer
        fields = ["bureau_local", "biographie", "signature_electronique"]
