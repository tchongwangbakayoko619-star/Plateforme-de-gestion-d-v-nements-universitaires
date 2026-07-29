from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Event
from .models import EventReview

INPUT_CLASSES = (
    "w-full rounded-card border border-primary-100 bg-paper px-3.5 py-2.5 "
    "text-sm text-ink placeholder:text-ink-muted "
    "focus:outline-none focus:ring-2 focus:ring-primary-500/30 "
    "focus:border-primary-500 transition-colors duration-150"
)

FILE_INPUT_CLASSES = (
    "block w-full text-sm text-ink-muted "
    "file:mr-4 file:rounded-card file:border-0 file:bg-primary-50 "
    "file:px-4 file:py-2 file:text-sm file:font-medium file:text-primary-600 "
    "hover:file:bg-primary-100"
)

CHECKBOX_CLASSES = (
    "h-5 w-5 rounded border-primary-100 text-primary-600 focus:ring-primary-500"
)

RADIO_CLASSES = "h-4 w-4 border-primary-100 text-primary-600 focus:ring-primary-500"


class StyledFormMixin:
    """Applique automatiquement les classes Tailwind du design system
    à chaque widget du formulaire, sans écraser les attrs déjà définis
    (type, rows, etc.) dans Meta.widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            existing = widget.attrs.get("class", "")
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = f"{existing} {CHECKBOX_CLASSES}".strip()
            elif isinstance(widget, forms.ClearableFileInput):
                widget.attrs["class"] = f"{existing} {FILE_INPUT_CLASSES}".strip()
            elif isinstance(widget, forms.RadioSelect | forms.CheckboxSelectMultiple):
                widget.attrs["class"] = f"{existing} {RADIO_CLASSES}".strip()
            else:
                widget.attrs["class"] = f"{existing} {INPUT_CLASSES}".strip()


class EventForm(StyledFormMixin, forms.ModelForm):
    """Formulaire de création/modification d'un événement par son
    organisateur.

    La logique de validation métier (statut modifiable, cohérence des
    dates) reste dans EventService — ce formulaire ne fait que la
    validation de forme.
    """

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pré-remplir les dates au format datetime-local (YYYY-MM-DDTHH:MM)
        if self.instance and self.instance.pk:
            if self.instance.date_debut:
                self.initial["date_debut"] = self.instance.date_debut.strftime(
                    "%Y-%m-%dT%H:%M",
                )
            if self.instance.date_fin:
                self.initial["date_fin"] = self.instance.date_fin.strftime(
                    "%Y-%m-%dT%H:%M",
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


class EventRefuserForm(StyledFormMixin, forms.Form):
    motif = forms.CharField(
        label=_("Motif du refus"),
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class EventRevisionForm(StyledFormMixin, forms.Form):
    commentaire = forms.CharField(
        label=_("Commentaire pour l'organisateur"),
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class EventAnnulerForm(StyledFormMixin, forms.Form):
    commentaire = forms.CharField(
        label=_("Motif de l'annulation"),
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
    )


class EventReviewForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = EventReview
        fields = ["note", "commentaire"]
        widgets = {
            "note": forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
            "commentaire": forms.Textarea(attrs={"rows": 3}),
        }
