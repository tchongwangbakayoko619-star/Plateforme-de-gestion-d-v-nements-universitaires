from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from gather.organizers.models import Organizer
from gather.students.models import Student


class Event(models.Model):
    """Événement universitaire. Contient uniquement les informations
    commerciales déclaratives — aucune logique de paiement ni d'inscription.
    """

    class Categorie(models.TextChoices):
        CONFERENCE = "conference", _("Conférence")
        ATELIER = "atelier", _("Atelier")
        CULTUREL = "culturel", _("Culturel")
        SPORTIF = "sportif", _("Sportif")
        ACADEMIQUE = "academique", _("Académique")
        AUTRE = "autre", _("Autre")

    class TypePaiement(models.TextChoices):
        GRATUIT = "gratuit", _("Gratuit")
        PAYANT = "payant", _("Payant")

    class Statut(models.TextChoices):
        DRAFT = "draft", _("Brouillon")
        PENDING = "pending", _("En attente de validation")
        REVISION_REQUESTED = "revision_requested", _("Révision demandée")
        PUBLISHED = "published", _("Publié")
        REJECTED = "rejected", _("Refusé")
        CANCELLED = "cancelled", _("Annulé")
        FINISHED = "finished", _("Terminé")
        ARCHIVED = "archived", _("Archivé")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    organizer = models.ForeignKey(
        Organizer,
        on_delete=models.CASCADE,
        related_name="evenements",
        verbose_name=_("Organisateur"),
    )

    titre = models.CharField(_("Titre"), max_length=200, db_index=True)
    description = models.TextField(_("Description"))
    categorie = models.CharField(
        _("Catégorie"),
        max_length=20,
        choices=Categorie.choices,
        default=Categorie.AUTRE,
        db_index=True,
    )
    image = models.ImageField(
        _("Image"),
        upload_to="events/images/%Y/%m/",
        blank=True,
        null=True,
    )

    lieu = models.CharField(_("Lieu"), max_length=255, db_index=True)
    latitude = models.DecimalField(
        _("Latitude"),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        _("Longitude"),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    date_debut = models.DateTimeField(_("Date de début"), db_index=True)
    date_fin = models.DateTimeField(_("Date de fin"), db_index=True)

    capacite_max = models.PositiveIntegerField(
        _("Capacité maximale"),
        validators=[MinValueValidator(1)],
    )
    places_restantes = models.PositiveIntegerField(_("Places restantes"))

    type_paiement = models.CharField(
        _("Type de paiement"),
        max_length=10,
        choices=TypePaiement.choices,
        default=TypePaiement.GRATUIT,
    )
    prix = models.DecimalField(
        _("Prix"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    devise = models.CharField(_("Devise"), max_length=3, default="XAF")

    statut = models.CharField(
        _("Statut"),
        max_length=25,
        choices=Statut.choices,
        default=Statut.DRAFT,
        db_index=True,
    )
    motif_refus = models.TextField(_("Motif de refus"), blank=True)
    published_at = models.DateTimeField(_("Publié le"), null=True, blank=True)

    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Modifié le"), auto_now=True)

    class Meta:
        verbose_name = _("Événement")
        verbose_name_plural = _("Événements")
        ordering = ["-date_debut"]
        indexes = [
            models.Index(fields=["statut", "date_debut"]),
            models.Index(fields=["organizer", "statut"]),
            models.Index(fields=["categorie", "statut"]),
            models.Index(fields=["titre"]),
            models.Index(fields=["lieu"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(date_fin__gt=models.F("date_debut")),
                name="event_date_fin_apres_date_debut",
            ),
            models.CheckConstraint(
                condition=models.Q(places_restantes__lte=models.F("capacite_max")),
                name="event_places_restantes_inferieur_capacite",
            ),
            models.CheckConstraint(
                condition=models.Q(capacite_max__gte=1),
                name="event_capacite_max_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.titre} ({self.get_statut_display()})"

    @property
    def est_publie(self) -> bool:
        return self.statut == self.Statut.PUBLISHED

    @property
    def peut_etre_supprime(self) -> bool:
        return self.statut in {
            self.Statut.DRAFT,
            self.Statut.REJECTED,
            self.Statut.REVISION_REQUESTED,
        }

    @property
    def est_termine(self) -> bool:
        return self.statut == self.Statut.FINISHED or (
            self.statut == self.Statut.PUBLISHED and self.date_fin <= timezone.now()
        )


class EventReview(models.Model):
    """Avis et note d'un étudiant sur un événement auquel il a participé."""

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="avis",
        verbose_name=_("Événement"),
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="avis_evenements",
        verbose_name=_("Étudiant"),
    )
    note = models.PositiveSmallIntegerField(
        _("Note"),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    commentaire = models.TextField(_("Commentaire"), blank=True)

    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Modifié le"), auto_now=True)

    class Meta:
        verbose_name = _("Avis événement")
        verbose_name_plural = _("Avis événements")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "student"],
                name="event_review_unique_par_etudiant",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student} — {self.event.titre} ({self.note}/5)"

    def clean(self) -> None:
        if not self.event.est_termine:
            message = _("Impossible de donner un avis sur un événement non terminé.")
            raise ValidationError(message)

    @staticmethod
    def moyenne_note(event: Event) -> float | None:
        agregat = EventReview.objects.filter(event=event).aggregate(
            moyenne=models.Avg("note"),
        )
        return agregat["moyenne"]

    @staticmethod
    def nombre_avis(event: Event) -> int:
        return EventReview.objects.filter(event=event).count()


class EventStatusHistory(models.Model):
    """Historique de chaque transition de statut d'un événement.
    Créé exclusivement via signal (voir signals.py) — jamais appelé
    directement par les services.
    """

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="historique_statuts",
        verbose_name=_("Événement"),
    )
    ancien_statut = models.CharField(
        _("Ancien statut"),
        max_length=25,
        choices=Event.Statut.choices,
        blank=True,
    )
    nouveau_statut = models.CharField(
        _("Nouveau statut"),
        max_length=25,
        choices=Event.Statut.choices,
    )
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Utilisateur"),
    )
    commentaire = models.TextField(_("Commentaire"), blank=True)
    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)

    class Meta:
        verbose_name = _("Historique de statut")
        verbose_name_plural = _("Historiques de statuts")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.event.titre} : {self.ancien_statut} → {self.nouveau_statut}"
