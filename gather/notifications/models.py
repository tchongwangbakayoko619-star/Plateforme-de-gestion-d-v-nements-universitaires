from __future__ import annotations

import uuid
from typing import ClassVar

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    class Type(models.TextChoices):
        EVENT_APPROUVE = "event_approuve", _("Événement approuvé")
        EVENT_REFUSE = "event_refuse", _("Événement refusé")
        EVENT_REVISION = "event_revision", _("Révision demandée")
        EVENT_PUBLIE = "event_publie", _("Événement publié")
        EVENT_MODIFIE = "event_modifie", _("Événement modifié")
        EVENT_ANNULE = "event_annule", _("Événement annulé")
        INSCRIPTION_CONFIRMEE = "inscription_confirmee", _("Inscription confirmée")
        PAIEMENT_CONFIRME = "paiement_confirme", _("Paiement confirmé")
        BILLET_DISPONIBLE = "billet_disponible", _("Billet disponible")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    destinataire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    type = models.CharField(_("Type"), max_length=30, choices=Type.choices)
    titre = models.CharField(_("Titre"), max_length=150)
    message = models.TextField(_("Message"))
    lien = models.CharField(_("Lien"), max_length=255, blank=True)
    lu = models.BooleanField(_("Lu"), default=False, db_index=True)
    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering: ClassVar[list[str]] = ["-created_at"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["destinataire", "lu"]),
        ]

    def __str__(self) -> str:
        return f"{self.destinataire.email} — {self.titre}"
