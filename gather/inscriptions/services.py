from __future__ import annotations

import io
import logging
import uuid
from typing import TYPE_CHECKING

import qrcode
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from gather.events.models import Event

from .models import Inscription
from .models import Ticket

if TYPE_CHECKING:
    from gather.students.models import Student

logger = logging.getLogger(__name__)


class InscriptionPermissionError(ValidationError):
    """Levée quand l'appelant n'a pas les droits sur l'inscription."""


class InscriptionService:
    """Toute la logique métier des inscriptions à un événement."""

    @staticmethod
    def _verifier_proprietaire(inscription: Inscription, student: Student) -> None:
        if inscription.student_id != student.id:
            message = "Vous ne pouvez agir que sur vos propres inscriptions."
            raise InscriptionPermissionError(message)

    @classmethod
    @transaction.atomic
    def s_inscrire(cls, student: Student, event: Event) -> Inscription:
        event_verrouille = Event.objects.select_for_update().get(pk=event.pk)

        if not event_verrouille.est_publie:
            message = "Seul un événement publié accepte des inscriptions."
            raise ValidationError(message)

        if event_verrouille.places_restantes <= 0:
            message = "Cet événement a atteint sa capacité maximale."
            raise ValidationError(message)

        if Inscription.objects.filter(
            event=event_verrouille,
            student=student,
            statut=Inscription.Statut.CONFIRMEE,
        ).exists():
            message = "Vous êtes déjà inscrit à cet événement."
            raise ValidationError(message)

        inscription = Inscription.objects.create(
            event=event_verrouille,
            student=student,
            statut=Inscription.Statut.CONFIRMEE,
        )

        Event.objects.filter(pk=event_verrouille.pk).update(
            places_restantes=F("places_restantes") - 1,
        )

        if event_verrouille.type_paiement == Event.TypePaiement.GRATUIT:
            TicketService.generer_billet(inscription)

        logger.info(
            "Inscription créée : %s -> %s",
            student.user.email,
            event_verrouille.titre,
        )
        return inscription

    @classmethod
    @transaction.atomic
    def annuler_inscription(
        cls,
        inscription: Inscription,
        student: Student,
    ) -> Inscription:
        cls._verifier_proprietaire(inscription, student)

        if not inscription.est_active:
            message = "Cette inscription est déjà annulée."
            raise ValidationError(message)

        inscription_verrouillee = Inscription.objects.select_for_update().get(
            pk=inscription.pk,
        )
        inscription_verrouillee.statut = Inscription.Statut.ANNULEE
        inscription_verrouillee.date_annulation = timezone.now()
        inscription_verrouillee.save(update_fields=["statut", "date_annulation"])

        Event.objects.filter(pk=inscription_verrouillee.event_id).update(
            places_restantes=F("places_restantes") + 1,
        )

        ticket = getattr(inscription_verrouillee, "ticket", None)
        if ticket and ticket.statut == Ticket.Statut.VALIDE:
            ticket.statut = Ticket.Statut.ANNULE
            ticket.save(update_fields=["statut"])

        logger.info(
            "Inscription annulée : %s -> %s",
            student.user.email,
            inscription_verrouillee.event.titre,
        )
        return inscription_verrouillee

    @staticmethod
    def get_inscriptions_etudiant(student: Student):
        return (
            Inscription.objects.filter(student=student)
            .select_related("event", "ticket")
            .order_by("-date_inscription")
        )

    @staticmethod
    def get_inscrits_evenement(event: Event):
        return (
            Inscription.objects.filter(
                event=event,
                statut=Inscription.Statut.CONFIRMEE,
            )
            .select_related("student__user", "ticket")
            .order_by("-date_inscription")
        )


class TicketService:
    """Génération et validation (check-in) des billets."""

    @staticmethod
    def _generer_qrcode_image(code_qr: str):
        img = qrcode.make(code_qr)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return ContentFile(buffer.getvalue(), name=f"{code_qr}.png")

    @classmethod
    @transaction.atomic
    def generer_billet(cls, inscription: Inscription) -> Ticket:
        if hasattr(inscription, "ticket"):
            return inscription.ticket

        code_qr = uuid.uuid4().hex
        ticket = Ticket(
            inscription=inscription,
            code_qr=code_qr,
            statut=Ticket.Statut.VALIDE,
        )
        ticket.image_qr.save(
            f"{code_qr}.png",
            cls._generer_qrcode_image(code_qr),
            save=False,
        )
        ticket.full_clean(exclude=["image_qr"])
        ticket.save()

        logger.info(
            "Billet généré : %s pour %s",
            code_qr,
            inscription.student.user.email,
        )
        return ticket

    @staticmethod
    @transaction.atomic
    def valider_qr_code(code_qr: str) -> dict:
        """Check-in : valide un billet, une seule fois."""
        try:
            ticket = (
                Ticket.objects.select_for_update()
                .select_related("inscription__student__user", "inscription__event")
                .get(code_qr=code_qr)
            )
        except Ticket.DoesNotExist:
            message = "Billet introuvable."
            raise ValidationError(message) from None

        if ticket.statut == Ticket.Statut.UTILISE:
            message = "Ce billet a déjà été utilisé."
            raise ValidationError(message)

        if ticket.statut == Ticket.Statut.ANNULE:
            message = "Ce billet a été annulé."
            raise ValidationError(message)

        ticket.statut = Ticket.Statut.UTILISE
        ticket.date_utilisation = timezone.now()
        ticket.save(update_fields=["statut", "date_utilisation"])

        return {
            "participant": ticket.inscription.student.user.get_full_name(),
            "evenement": ticket.inscription.event.titre,
            "heure": ticket.date_utilisation.isoformat(),
            "statut": ticket.statut,
        }
