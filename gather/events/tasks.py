# gather/events/tasks.py
from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Event
from .services import EventService

logger = logging.getLogger(__name__)


@shared_task
def terminer_evenements_expires() -> int:
    """
    Tâche planifiée (via django_celery_beat) : cherche tous les événements
    publiés dont la date de fin est dépassée et les fait passer à FINISHED.
    Retourne le nombre d'événements traités.
    """
    evenements_expires = Event.objects.filter(
        statut=Event.Statut.PUBLISHED,
        date_fin__lte=timezone.now(),
    )

    count = 0
    for event in evenements_expires:
        try:
            EventService.terminer_automatiquement(event)
        except Exception:
            logger.exception(
                "Échec de terminaison automatique pour l'événement %s",
                event.id,
            )
        else:
            count += 1

    logger.info("%d événement(s) marqué(s) comme terminé(s).", count)
    return count


def _lien_absolu(chemin: str) -> str:
    """URL absolue nécessaire dans un email : pas de request disponible
    dans une tâche Celery pour build_absolute_uri()."""
    current_site = Site.objects.get_current()
    protocole = "http" if settings.DEBUG else "https"
    return f"{protocole}://{current_site.domain}{chemin}"


@shared_task(bind=True, max_retries=3, default_retry_delay=60, rate_limit="10/m")
def notifier_organisateur_evenement_approuve(self, event_id: int) -> None:
    """Notifie l'organisateur que son événement a été approuvé et publié."""
    try:
        event = Event.objects.select_related("organizer__user").get(pk=event_id)
    except Event.DoesNotExist:
        logger.warning("Événement %s introuvable, notification annulée.", event_id)
        return

    organisateur_user = event.organizer.user
    lien = _lien_absolu(f"/events/{event.id}/")
    context = {
        "event": event,
        "organisateur_first_name": organisateur_user.first_name,
        "lien_event": lien,
    }
    html_message = render_to_string("emails/events/evenement_approuve.html", context)

    try:
        send_mail(
            subject=f"Votre événement « {event.titre} » est publié !",
            message=(
                f"Bonjour {organisateur_user.first_name},\n\n"
                f"Votre événement « {event.titre} » a été approuvé et est "
                f"maintenant visible publiquement.\n\n"
                f"Voir l'événement : {lien}\n"
            ),
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[organisateur_user.email],
            fail_silently=False,
        )
        logger.info(
            "Notification approbation envoyée à %s pour %s",
            organisateur_user.email,
            event.titre,
        )
    except Exception as exc:
        logger.exception("Échec notification approbation pour événement %s", event_id)
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=3, default_retry_delay=60, rate_limit="10/m")
def notifier_organisateur_evenement_refuse(self, event_id: int, motif: str) -> None:
    """Notifie l'organisateur que son événement a été refusé, avec motif."""
    try:
        event = Event.objects.select_related("organizer__user").get(pk=event_id)
    except Event.DoesNotExist:
        logger.warning("Événement %s introuvable, notification annulée.", event_id)
        return

    organisateur_user = event.organizer.user
    lien = _lien_absolu(f"/events/organisateur/{event.id}/")
    context = {
        "event": event,
        "organisateur_first_name": organisateur_user.first_name,
        "motif": motif,
        "lien_event": lien,
    }
    html_message = render_to_string("emails/events/evenement_refuse.html", context)

    try:
        send_mail(
            subject=f"Votre événement « {event.titre} » n'a pas été approuvé",
            message=(
                f"Bonjour {organisateur_user.first_name},\n\n"
                f"Votre événement « {event.titre} » a été refusé.\n"
                f"Motif : {motif or 'Non précisé'}\n\n"
                f"Consultez-le ici : {lien}\n"
            ),
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[organisateur_user.email],
            fail_silently=False,
        )
        logger.info(
            "Notification refus envoyée à %s pour %s",
            organisateur_user.email,
            event.titre,
        )
    except Exception as exc:
        logger.exception("Échec notification refus pour événement %s", event_id)
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=3, default_retry_delay=60, rate_limit="10/m")
def notifier_organisateur_revision_demandee(
    self,
    event_id: int,
    commentaire: str,
) -> None:
    """Notifie l'organisateur qu'une révision de son événement est demandée."""
    try:
        event = Event.objects.select_related("organizer__user").get(pk=event_id)
    except Event.DoesNotExist:
        logger.warning("Événement %s introuvable, notification annulée.", event_id)
        return

    organisateur_user = event.organizer.user
    lien = _lien_absolu(f"/events/organisateur/{event.id}/modifier/")
    context = {
        "event": event,
        "organisateur_first_name": organisateur_user.first_name,
        "commentaire": commentaire,
        "lien_event": lien,
    }
    html_message = render_to_string("emails/events/revision_demandee.html", context)

    try:
        send_mail(
            subject=f"Modifications demandées pour « {event.titre} »",
            message=(
                f"Bonjour {organisateur_user.first_name},\n\n"
                f"L'administrateur demande des modifications sur "
                f"« {event.titre} ».\n"
                f"Commentaire : {commentaire}\n\n"
                f"Modifiez-le ici : {lien}\n"
            ),
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[organisateur_user.email],
            fail_silently=False,
        )
        logger.info(
            "Notification révision envoyée à %s pour %s",
            organisateur_user.email,
            event.titre,
        )
    except Exception as exc:
        logger.exception("Échec notification révision pour événement %s", event_id)
        raise self.retry(exc=exc) from exc
