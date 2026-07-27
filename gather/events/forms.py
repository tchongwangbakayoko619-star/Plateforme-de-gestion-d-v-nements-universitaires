from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Event
from .models import EventReview


class EventForm(forms.ModelForm):
    """Formulaire de création/modification d'un événement par son
    organisateur. La logique de validation métier (statut modifiable,
    cohérence des dates) reste dans EventService — ce formulaire ne fait
    que la validation de forme."""

    class Meta:
        model = Event
        fields = [
            "titre",
            "description",
            "categorie",
            "statut",
            "image",
            "lieu",
            "latitude",
            "longitude",
            "date_debut",
            "date_fin",
            "capacite_max",
            "type_paiement",
            "prix",
            "devise",
        ]
        widgets = {
            "date_debut": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "date_fin": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "description": forms.Textarea(attrs={"rows": 5}),
        }

    statut = forms.ChoiceField(
        choices=[
            (Event.Statut.DRAFT, Event.Statut.DRAFT.label),
            (Event.Statut.PENDING, Event.Statut.PENDING.label),
        ],
        label=_("Statut"),
        initial=Event.Statut.DRAFT,
    )

    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get("date_debut")
        date_fin = cleaned_data.get("date_fin")
        if date_debut and date_fin and date_fin <= date_debut:
            self.add_error(
                "date_fin",
                _("La date de fin doit être postérieure à la date de début."),
            )
        return cleaned_data


class EventRefuserForm(forms.Form):
    motif = forms.CharField(
        label=_("Motif du refus"),
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class EventRevisionForm(forms.Form):
    commentaire = forms.CharField(
        label=_("Commentaire pour l'organisateur"),
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class EventAnnulerForm(forms.Form):
    commentaire = forms.CharField(
        label=_("Motif de l'annulation"),
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
    )


class EventReviewForm(forms.ModelForm):
    class Meta:
        model = EventReview
        fields = ["note", "commentaire"]
        widgets = {
            "note": forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
            "commentaire": forms.Textarea(attrs={"rows": 3}),
        }
