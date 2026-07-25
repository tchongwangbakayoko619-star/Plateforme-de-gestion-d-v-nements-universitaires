# gather/events/signals.py
from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

from django.db import transaction
from django.dispatch import Signal
from django.dispatch import receiver

from .models import Event
from .models import EventStatusHistory

event_status_changed = Signal()


@dataclass(frozen=True)
class StatusChangeContext:
    """Regroupe les infos d'une transition de statut pour éviter un
    signal avec trop de paramètres positionnels (PLR0913)."""

    event: Event
    ancien_statut: str
    nouveau_statut: str
    utilisateur: object | None = None
    commentaire: str = field(default="")


@receiver(event_status_changed)
def create_status_history(sender, context: StatusChangeContext, **kwargs):
    """Crée un historique lorsqu'une transition de statut est validée."""
    EventStatusHistory.objects.create(
        event=context.event,
        ancien_statut=context.ancien_statut,
        nouveau_statut=context.nouveau_statut,
        utilisateur=context.utilisateur,
        commentaire=context.commentaire,
    )


@receiver(event_status_changed)
def notifier_organisateur_apres_decision_admin(
    sender,
    context: StatusChangeContext,
    **kwargs,
):
    """
    Notifie l'organisateur quand l'admin statue sur son événement soumis
    (approbation, refus, ou demande de révision).

    transaction.on_commit() garantit que l'email n'est déclenché que si
    la transaction contenant le changement de statut aboutit réellement.

    L'import de .tasks reste local et volontaire : events.tasks importe
    des modèles/services qui, à terme, pourraient référencer signals.py
    au chargement de l'app (via apps.py -> ready()). Un import en tête
    de ce fichier créerait un cycle d'import au démarrage de Django.
    """
    from .tasks import notifier_organisateur_evenement_approuve  # noqa: PLC0415
    from .tasks import notifier_organisateur_evenement_refuse  # noqa: PLC0415
    from .tasks import notifier_organisateur_revision_demandee  # noqa: PLC0415

    event_id = context.event.id
    commentaire = context.commentaire

    if context.nouveau_statut == Event.Statut.PUBLISHED:
        transaction.on_commit(
            lambda: notifier_organisateur_evenement_approuve.delay(event_id),
        )
    elif context.nouveau_statut == Event.Statut.REJECTED:
        transaction.on_commit(
            lambda: notifier_organisateur_evenement_refuse.delay(
                event_id,
                commentaire,
            ),
        )
    elif context.nouveau_statut == Event.Statut.REVISION_REQUESTED:
        transaction.on_commit(
            lambda: notifier_organisateur_revision_demandee.delay(
                event_id,
                commentaire,
            ),
        )
