from __future__ import annotations

import datetime
import logging

from celery import shared_task
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from gather.events.models import Event
from gather.notifications.models import Notification
from gather.notifications.services import NotificationService

from .models import Inscription

logger = logging.getLogger(__name__)

DELAI_RAPPEL_HEURES = 24


def _lien_absolu(chemin: str) -> str:
    current_site = Site.objects.get_current()
    protocole = "http" if settings.DEBUG else "https"
    return f"{protocole}://{current_site.domain}{chemin}"


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def envoyer_rappels_24h(self) -> dict:
    """Tâche planifiée (Celery Beat) : cherche les événements publiés
    dont le début est dans 24h (+/- la fenêtre d'exécution du beat) et
    envoie un rappel (email + notification WebSocket) à chaque étudiant
    inscrit, une seule fois par événement."""
    maintenant = timezone.now()
    borne_basse = maintenant + datetime.timedelta(hours=DELAI_RAPPEL_HEURES)
    borne_haute = borne_basse + datetime.timedelta(minutes=15)

    evenements = Event.objects.filter(
        statut=Event.Statut.PUBLISHED,
        date_debut__gte=borne_basse,
        date_debut__lt=borne_haute,
    )

    total_rappels = 0
    for event in evenements:
        inscriptions = Inscription.objects.filter(
            event=event,
            statut=Inscription.Statut.CONFIRMEE,
        ).select_related("student__user")

        for inscription in inscriptions:
            _envoyer_rappel_email(inscription)
            _envoyer_rappel_notification(inscription)
            total_rappels += 1

    logger.info("Rappels 24h envoyés : %d", total_rappels)
    return {"total_rappels": total_rappels}


def _envoyer_rappel_email(inscription: Inscription) -> None:
    student_user = inscription.student.user
    event = inscription.event
    lien = _lien_absolu(f"/events/{event.id}/")

    context = {
        "event": event,
        "student_first_name": student_user.first_name,
        "lien_event": lien,
    }
    html_message = render_to_string("emails/inscriptions/rappel_24h.html", context)

    try:
        send_mail(
            subject=f"Rappel — « {event.titre} » a lieu demain",
            message=(
                f"Bonjour {student_user.first_name},\n\n"
                f"Rappel : « {event.titre} » a lieu demain, "
                f"{event.date_debut.strftime('%d/%m/%Y à %H:%M')}.\n\n"
                f"Détails : {lien}\n"
            ),
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student_user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Échec d'envoi du rappel email à %s", student_user.email)


def _envoyer_rappel_notification(inscription: Inscription) -> None:
    event = inscription.event
    NotificationService.creer(
        destinataire=inscription.student.user,
        type_notification=Notification.Type.EVENT_MODIFIE,
        titre="Rappel : événement demain",
        message=(
            f"« {event.titre} » a lieu demain à {event.date_debut.strftime('%H:%M')}."
        ),
        lien=f"/events/{event.id}/",
    )
