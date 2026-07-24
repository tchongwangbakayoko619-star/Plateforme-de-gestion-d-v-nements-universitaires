# gather/students/forms.py
from django import forms

from .models import Student


class StudentProfileForm(forms.ModelForm):
    """Formulaire self-service : seuls les champs personnels sont éditables.
    matricule, filiere, departement, niveau_etude, promotion et
    statut_academique restent réservés à l'admin (données institutionnelles).
    """

    class Meta:
        model = Student
        fields = ["groupe", "date_naissance", "sexe", "photo_carte_etudiante"]
        widgets = {
            "date_naissance": forms.DateInput(attrs={"type": "date"}),
        }
