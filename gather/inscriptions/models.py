# gather/inscriptions/models.py
from __future__ import annotations

import uuid
from typing import ClassVar

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from gather.events.models import Event
from gather.students.models import Student


class Inscription(models.Model):
    """Inscription d'un étudiant à un événement. Le décrément/incrément
    de `Event.places_restantes` est géré exclusivement par
    InscriptionService, jamais ici."""

    class Statut(models.TextChoices):
        EN_ATTENTE_PAIEMENT = "en_attente_paiement", _("En attente de paiement")
        CONFIRMEE = "confirmee", _("Confirmée")
        ANNULEE = "annulee", _("Annulée")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="inscriptions",
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="inscriptions",
    )
    statut = models.CharField(
        _("Statut"),
        max_length=25,
        choices=Statut.choices,
        default=Statut.CONFIRMEE,
        db_index=True,
    )
    date_inscription = models.DateTimeField(_("Inscrit le"), auto_now_add=True)
    date_annulation = models.DateTimeField(_("Annulé le"), null=True, blank=True)

    class Meta:
        verbose_name = _("Inscription")
        verbose_name_plural = _("Inscriptions")
        ordering: ClassVar[list[str]] = ["-date_inscription"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["event", "student"],
                condition=models.Q(statut="confirmee"),
                name="inscription_active_unique_par_etudiant_et_evenement",
            ),
            models.UniqueConstraint(
                fields=["event", "student"],
                condition=models.Q(statut="en_attente_paiement"),
                name="inscription_attente_unique_par_etudiant_et_evenement",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["event", "statut"]),
            models.Index(fields=["student", "statut"]),
        ]

    def __str__(self) -> str:
        return f"{self.student} -> {self.event} ({self.statut})"

    @property
    def est_active(self) -> bool:
        return self.statut in {self.Statut.CONFIRMEE, self.Statut.EN_ATTENTE_PAIEMENT}

    @property
    def necessite_paiement(self) -> bool:
        return self.statut == self.Statut.EN_ATTENTE_PAIEMENT


class Ticket(models.Model):
    """Billet généré pour une inscription. Gratuit : immédiatement après
    inscription. Payant : uniquement après confirmation du paiement
    (le module paiements appellera TicketService.generer_billet)."""

    class Statut(models.TextChoices):
        VALIDE = "valide", _("Valide")
        UTILISE = "utilise", _("Utilisé")
        ANNULE = "annule", _("Annulé")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inscription = models.OneToOneField(
        Inscription,
        on_delete=models.CASCADE,
        related_name="ticket",
    )
    code_qr = models.CharField(_("Code QR"), max_length=64, unique=True, db_index=True)
    image_qr = models.ImageField(
        _("Image QR"),
        upload_to="tickets/qrcodes/%Y/%m/",
        blank=True,
        null=True,
    )
    statut = models.CharField(
        _("Statut"),
        max_length=15,
        choices=Statut.choices,
        default=Statut.VALIDE,
        db_index=True,
    )
    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)
    date_utilisation = models.DateTimeField(_("Utilisé le"), null=True, blank=True)

    class Meta:
        verbose_name = _("Billet")
        verbose_name_plural = _("Billets")
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self) -> str:
        return f"Billet {self.code_qr} — {self.inscription.event.titre}"

    def clean(self) -> None:
        if self.statut == self.Statut.UTILISE and not self.date_utilisation:
            message = "Un billet utilisé doit avoir une date d'utilisation."
            raise ValidationError(message)
