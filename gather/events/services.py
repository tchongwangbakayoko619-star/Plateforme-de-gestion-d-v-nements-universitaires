# gather/events/services.py
from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.db.models import Avg
from django.db.models import Count
from django.db.models import Q
from django.db.models import QuerySet
from django.utils import timezone

from .models import Event
from .models import EventReview
from .signals import StatusChangeContext
from .signals import event_status_changed

logger = logging.getLogger(__name__)


class InvalidTransitionError(Exception):
    """Levée lors d'une transition de statut non autorisée par la machine
    d'états."""


class EventPermissionError(Exception):
    """Levée quand l'appelant n'a pas les droits nécessaires sur
    l'événement ou l'action demandée."""


class EventService:
    """Logique métier liée au cycle de vie d'un événement."""

    TRANSITIONS: dict[str, set[str]] = {
        Event.Statut.DRAFT: {Event.Statut.PENDING},
        Event.Statut.PENDING: {
            Event.Statut.PUBLISHED,
            Event.Statut.REJECTED,
            Event.Statut.REVISION_REQUESTED,
        },
        Event.Statut.REVISION_REQUESTED: {
            Event.Statut.DRAFT,
            Event.Statut.PENDING,
        },
        Event.Statut.PUBLISHED: {
            Event.Statut.CANCELLED,
            Event.Statut.FINISHED,
        },
        Event.Statut.REJECTED: {Event.Statut.ARCHIVED},
        Event.Statut.CANCELLED: {Event.Statut.ARCHIVED},
        Event.Statut.FINISHED: {Event.Statut.ARCHIVED},
        Event.Statut.ARCHIVED: set(),
    }

    # Permissions
    @staticmethod
    def check_est_proprietaire(event: Event, organizer) -> None:
        if event.organizer_id != organizer.id:
            message = "Vous n'êtes pas l'organisateur de cet événement."
            raise EventPermissionError(message)

    @staticmethod
    def check_est_admin(admin_user) -> None:
        if not getattr(admin_user, "is_administrateur", False):
            message = "Seul un administrateur peut effectuer cette action."
            raise EventPermissionError(message)

    # Actions Organizer : création, modification, suppression
    @staticmethod
    def creer_brouillon(organizer, data: dict) -> Event:
        return Event.objects.create(
            organizer=organizer,
            titre=data["titre"],
            description=data["description"],
            categorie=data.get("categorie", Event.Categorie.AUTRE),
            image=data.get("image"),
            lieu=data["lieu"],
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            date_debut=data["date_debut"],
            date_fin=data["date_fin"],
            capacite_max=data["capacite_max"],
            places_restantes=data["capacite_max"],
            type_paiement=data.get("type_paiement", Event.TypePaiement.GRATUIT),
            prix=data.get("prix"),
            devise=data.get("devise", "XAF"),
            statut=data.get("statut", Event.Statut.DRAFT),
        )

    @staticmethod
    def modifier(event: Event, data: dict, organizer) -> Event:
        EventService.check_est_proprietaire(event, organizer)

        if event.statut not in {Event.Statut.DRAFT, Event.Statut.REVISION_REQUESTED}:
            message = (
                "Seuls les brouillons ou les événements en révision "
                "peuvent être modifiés."
            )
            raise ValidationError(message)

        champs_modifiables = [
            "titre",
            "description",
            "categorie",
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
            "statut",
        ]

        # Sauvegarder le nouveau statut avant de modifier
        nouveau_statut = data.get("statut")
        ancien_statut = event.statut

        # Appliquer les modifications sur les champs (sauf statut pour l'instant)
        for champ in champs_modifiables:
            if champ in data and champ != "statut":
                setattr(event, champ, data[champ])

        if "capacite_max" in data:
            event.places_restantes = data["capacite_max"]

        # Si le statut change, gérer via la machine d'états
        if nouveau_statut and nouveau_statut != ancien_statut:
            if (
                nouveau_statut == Event.Statut.PENDING
                and ancien_statut == Event.Statut.DRAFT
            ):
                # Sauvegarder les modifs puis soumettre
                event.full_clean()
                event.save()
                return EventService.soumettre(event, organizer)
            if (
                nouveau_statut == Event.Statut.DRAFT
                and ancien_statut == Event.Statut.REVISION_REQUESTED
            ):
                # Retour en brouillon sans transition officielle
                event.statut = Event.Statut.DRAFT
                event.full_clean()
                event.save()
                return event
            # Autre changement de statut non supporté
            event.statut = ancien_statut  # restore
            message = (
                f"Transition non autorisée de {ancien_statut} vers {nouveau_statut}."
            )
            raise ValidationError(message)
        # Mise à jour normale, sans changement de statut
        event.full_clean()
        event.save()
        return event

    @staticmethod
    def supprimer(event: Event, organizer) -> None:
        EventService.check_est_proprietaire(event, organizer)

        if not event.peut_etre_supprime:
            message = (
                "Seuls les brouillons, refusés ou en révision peuvent être supprimés."
            )
            raise ValidationError(message)

        event.delete()

    # Machine d'états
    @staticmethod
    def _transition(
        event: Event,
        nouveau_statut: str,
        utilisateur=None,
        commentaire: str = "",
    ) -> Event:
        ancien_statut = event.statut

        if nouveau_statut not in EventService.TRANSITIONS.get(ancien_statut, set()):
            message = f"Transition impossible de {ancien_statut} vers {nouveau_statut}."
            raise InvalidTransitionError(message)

        event.statut = nouveau_statut
        if nouveau_statut == Event.Statut.PUBLISHED:
            event.published_at = timezone.now()
        event.save()

        # Seule la création de l'historique et la notification passent
        # par ce signal — aucune autre logique métier n'y est déléguée.
        event_status_changed.send(
            sender=Event,
            context=StatusChangeContext(
                event=event,
                ancien_statut=ancien_statut,
                nouveau_statut=nouveau_statut,
                utilisateur=utilisateur,
                commentaire=commentaire,
            ),
        )

        logger.info(
            "Événement %s : %s -> %s (par %s)",
            event.id,
            ancien_statut,
            nouveau_statut,
            getattr(utilisateur, "email", "système"),
        )
        return event

    @staticmethod
    def soumettre(event: Event, organizer) -> Event:
        EventService.check_est_proprietaire(event, organizer)
        return EventService._transition(
            event,
            Event.Statut.PENDING,
            utilisateur=organizer.user,
        )

    @staticmethod
    def approuver(event: Event, admin_user) -> Event:
        EventService.check_est_admin(admin_user)
        return EventService._transition(
            event,
            Event.Statut.PUBLISHED,
            utilisateur=admin_user,
        )

    @staticmethod
    def refuser(event: Event, admin_user, motif: str = "") -> Event:
        EventService.check_est_admin(admin_user)
        if motif:
            event.motif_refus = motif
            event.save(update_fields=["motif_refus"])
        return EventService._transition(
            event,
            Event.Statut.REJECTED,
            utilisateur=admin_user,
            commentaire=motif,
        )

    @staticmethod
    def demander_revision(event: Event, admin_user, commentaire: str = "") -> Event:
        EventService.check_est_admin(admin_user)
        return EventService._transition(
            event,
            Event.Statut.REVISION_REQUESTED,
            utilisateur=admin_user,
            commentaire=commentaire,
        )

    @staticmethod
    def annuler(event: Event, admin_user, commentaire: str = "") -> Event:
        EventService.check_est_admin(admin_user)
        return EventService._transition(
            event,
            Event.Statut.CANCELLED,
            utilisateur=admin_user,
            commentaire=commentaire,
        )

    @staticmethod
    def archiver(event: Event, admin_user) -> Event:
        EventService.check_est_admin(admin_user)
        return EventService._transition(
            event,
            Event.Statut.ARCHIVED,
            utilisateur=admin_user,
        )

    @staticmethod
    def terminer_automatiquement(event: Event) -> Event:
        """Appelée par la tâche planifiée, jamais par un utilisateur —
        pas de vérification de permission ici."""
        if event.statut == Event.Statut.PUBLISHED and event.date_fin <= timezone.now():
            return EventService._transition(event, Event.Statut.FINISHED)
        return event

    # Lecture
    @staticmethod
    def get_evenement(event_id) -> Event:
        return Event.objects.select_related("organizer").get(pk=event_id)

    @staticmethod
    def get_evenements(filters: dict | None = None) -> QuerySet[Event]:
        queryset = Event.objects.select_related("organizer").prefetch_related("avis")

        if not filters:
            return queryset

        if filters.get("statut"):
            queryset = queryset.filter(statut=filters["statut"])
        if filters.get("categorie"):
            queryset = queryset.filter(categorie=filters["categorie"])
        if filters.get("date_debut"):
            queryset = queryset.filter(date_debut__gte=filters["date_debut"])
        if filters.get("date_fin"):
            queryset = queryset.filter(date_fin__lte=filters["date_fin"])
        if filters.get("organisateur_id"):
            queryset = queryset.filter(organizer_id=filters["organisateur_id"])
        if filters.get("search"):
            search = filters["search"]
            queryset = queryset.filter(
                Q(titre__icontains=search)
                | Q(description__icontains=search)
                | Q(lieu__icontains=search),
            )
        return queryset

    @staticmethod
    def get_evenements_publics() -> QuerySet[Event]:
        return Event.objects.filter(statut=Event.Statut.PUBLISHED).select_related(
            "organizer",
        )


class ReviewService:
    """Logique métier liée aux avis et notes des étudiants."""

    @staticmethod
    def _verifier_participation(student, event: Event) -> None:
        """Point d'extension : la vérification réelle de participation
        (présence à l'événement) dépend du futur module d'inscriptions,
        volontairement hors périmètre ici. Ne fait rien pour l'instant —
        à brancher sur le module inscriptions/tickets une fois créé."""

    @staticmethod
    def ajouter_avis(
        student,
        event: Event,
        note: int,
        commentaire: str = "",
    ) -> EventReview:
        if not event.est_termine:
            message = "Impossible de donner un avis sur un événement non terminé."
            raise ValidationError(message)

        if EventReview.objects.filter(event=event, student=student).exists():
            message = "Vous avez déjà donné un avis pour cet événement."
            raise ValidationError(message)

        ReviewService._verifier_participation(student, event)

        review = EventReview(
            event=event,
            student=student,
            note=note,
            commentaire=commentaire,
        )
        review.full_clean()
        review.save()
        return review

    @staticmethod
    def modifier_avis(
        review: EventReview,
        student,
        note: int,
        commentaire: str = "",
    ) -> EventReview:
        if review.student_id != student.id:
            message = "Vous ne pouvez modifier que votre propre avis."
            raise EventPermissionError(message)

        review.note = note
        review.commentaire = commentaire
        review.full_clean()
        review.save()
        return review

    @staticmethod
    def supprimer_avis(review: EventReview, student) -> None:
        if review.student_id != student.id:
            message = "Vous ne pouvez supprimer que votre propre avis."
            raise EventPermissionError(message)
        review.delete()

    @staticmethod
    def get_avis_evenement(event: Event) -> QuerySet[EventReview]:
        return EventReview.objects.filter(event=event).select_related(
            "student",
            "student__user",
        )

    @staticmethod
    def get_stats_evenement(event: Event) -> dict:
        avis = EventReview.objects.filter(event=event)
        return {
            "moyenne": avis.aggregate(moyenne=Avg("note"))["moyenne"],
            "nombre_avis": avis.count(),
            "repartition": list(
                avis.values("note").annotate(count=Count("note")).order_by("note"),
            ),
        }
