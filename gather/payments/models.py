# gather/payments/models.py
from __future__ import annotations

import uuid
from typing import ClassVar

from django.db import models
from django.utils.translation import gettext_lazy as _

from gather.inscriptions.models import Inscription


class Payment(models.Model):
    """Paiement lié à une inscription à un événement payant. Le statut
    n'est modifié que par PaymentService, jamais directement."""

    app_label = "payments"

    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", _("En attente")
        REUSSI = "reussi", _("Réussi")
        ECHOUE = "echoue", _("Échoué")
        REMBOURSE = "rembourse", _("Remboursé")

    class Provider(models.TextChoices):
        CAMPAY = "campay", _("CamPay")
        STRIPE = "stripe", _("Stripe")
        CINETPAY = "cinetpay", _("CinetPay")
        FLUTTERWAVE = "flutterwave", _("Flutterwave")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inscription = models.OneToOneField(
        Inscription,
        on_delete=models.CASCADE,
        related_name="paiement",
    )
    provider = models.CharField(
        _("Fournisseur"),
        max_length=20,
        choices=Provider.choices,
        default=Provider.CAMPAY,
    )
    montant = models.DecimalField(_("Montant"), max_digits=10, decimal_places=2)
    devise = models.CharField(_("Devise"), max_length=3, default="XAF")
    telephone = models.CharField(_("Téléphone Mobile Money"), max_length=20)
    reference_externe = models.CharField(
        _("Référence externe"),
        max_length=100,
        unique=True,
        db_index=True,
    )
    statut = models.CharField(
        _("Statut"),
        max_length=15,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE,
        db_index=True,
    )
    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Modifié le"), auto_now=True)

    class Meta:
        verbose_name = _("Paiement")
        verbose_name_plural = _("Paiements")
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"{self.reference_externe} — {self.montant} {self.devise} ({self.statut})"
        )


class PaymentTransaction(models.Model):
    """Journal de chaque appel/réponse fournisseur — utile pour le débogage
    et l'audit, jamais modifié après création (append-only)."""

    app_label = "payments"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    evenement = models.CharField(_("Événement"), max_length=50)
    payload_brut = models.JSONField(_("Payload brut"), default=dict)
    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)

    class Meta:
        verbose_name = _("Transaction de paiement")
        verbose_name_plural = _("Transactions de paiement")
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.payment.reference_externe} — {self.evenement}"
