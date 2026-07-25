"""Branchement des notifications sur les événements métier existants."""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from gather.events.models import Event
from gather.events.signals import event_status_changed
from gather.inscriptions.models import Inscription
from gather.payments.models import Payment

from .models import Notification
from .services import NotificationService

logger = logging.getLogger(__name__)


@receiver(event_status_changed)
def notifier_organisateur_changement_statut(  # noqa: PLR0913
    sender,
    event,
    ancien_statut,
    nouveau_statut,
    utilisateur=None,
    commentaire="",
    **kwargs,
):
    mapping_types = {
        Event.Statut.PUBLISHED: (
            Notification.Type.EVENT_PUBLIE,
            "Votre événement a été publié",
        ),
        Event.Statut.REJECTED: (
            Notification.Type.EVENT_REFUSE,
            "Votre événement a été refusé",
        ),
        Event.Statut.REVISION_REQUESTED: (
            Notification.Type.EVENT_REVISION,
            "Une révision est demandée sur votre événement",
        ),
        Event.Statut.CANCELLED: (
            Notification.Type.EVENT_ANNULE,
            "Votre événement a été annulé",
        ),
    }

    entree = mapping_types.get(nouveau_statut)
    if entree is None:
        return

    type_notif, titre = entree
    NotificationService.creer(
        destinataire=event.organizer.user,
        type_notification=type_notif,
        titre=titre,
        message=f"« {event.titre} » : {commentaire or titre}.",
        lien=f"/events/organizer/{event.id}/",
    )

    if nouveau_statut == Event.Statut.PUBLISHED:
        _notifier_inscrits(
            event,
            Notification.Type.EVENT_PUBLIE,
            "Un événement auquel vous participez est publié",
        )
    elif nouveau_statut == Event.Statut.CANCELLED:
        _notifier_inscrits(
            event,
            Notification.Type.EVENT_ANNULE,
            "Un événement auquel vous êtes inscrit a été annulé",
        )


def _notifier_inscrits(event: Event, type_notif: str, titre: str) -> None:
    inscriptions = Inscription.objects.filter(
        event=event,
        statut=Inscription.Statut.CONFIRMEE,
    ).select_related("student__user")
    for inscription in inscriptions:
        NotificationService.creer(
            destinataire=inscription.student.user,
            type_notification=type_notif,
            titre=titre,
            message=f"« {event.titre} » : {titre}.",
            lien=f"/events/{event.id}/",
        )


@receiver(post_save, sender=Inscription)
def notifier_inscription_confirmee(sender, instance, created, **kwargs):
    if created and instance.statut == Inscription.Statut.CONFIRMEE:
        NotificationService.creer(
            destinataire=instance.student.user,
            type_notification=Notification.Type.INSCRIPTION_CONFIRMEE,
            titre="Inscription confirmée",
            message=f"Votre inscription à « {instance.event.titre} » est confirmée.",
            lien=f"/events/{instance.event.id}/",
        )


@receiver(post_save, sender=Payment)
def notifier_paiement_confirme(sender, instance, created, **kwargs):
    if not created and instance.statut == Payment.Statut.REUSSI:
        NotificationService.creer(
            destinataire=instance.inscription.student.user,
            type_notification=Notification.Type.PAIEMENT_CONFIRME,
            titre="Paiement confirmé",
            message=(
                f"Votre paiement de {instance.montant} {instance.devise} pour "
                f"« {instance.inscription.event.titre} » est confirmé."
            ),
            lien=f"/events/{instance.inscription.event.id}/",
        )
        if hasattr(instance.inscription, "ticket"):
            NotificationService.creer(
                destinataire=instance.inscription.student.user,
                type_notification=Notification.Type.BILLET_DISPONIBLE,
                titre="Votre billet est disponible",
                message=(
                    f"Votre billet pour « {instance.inscription.event.titre} » "
                    f"est prêt."
                ),
                lien="/inscriptions/mes-inscriptions/",
            )
