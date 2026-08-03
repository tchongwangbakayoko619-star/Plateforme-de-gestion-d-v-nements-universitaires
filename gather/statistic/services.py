# gather/statistics/services.py
from __future__ import annotations

from django.db.models import Avg
from django.db.models import Count
from django.db.models import ExpressionWrapper
from django.db.models import F
from django.db.models import FloatField
from django.db.models import Sum

from gather.events.models import Event
from gather.events.models import EventReview
from gather.inscriptions.models import Inscription
from gather.payments.models import Payment


class StatisticsService:
    """Toute la logique de calcul statistique centralisée ici — les vues
    ne font qu'appeler ces méthodes et sérialiser le résultat."""

    @staticmethod
    def statistiques_globales() -> dict:
        """Vue d'ensemble plateforme, réservée à l'administrateur."""
        evenements = Event.objects.all()
        paiements_reussis = Payment.objects.filter(statut=Payment.Statut.REUSSI)
        inscriptions_confirmees = Inscription.objects.filter(
            statut=Inscription.Statut.CONFIRMEE,
        )

        return {
            "evenements_publies": evenements.filter(
                statut=Event.Statut.PUBLISHED,
            ).count(),
            "evenements_annules": evenements.filter(
                statut=Event.Statut.CANCELLED,
            ).count(),
            "evenements_termines": evenements.filter(
                statut=Event.Statut.FINISHED,
            ).count(),
            "total_participants": inscriptions_confirmees.count(),
            "revenus_total": paiements_reussis.aggregate(total=Sum("montant"))["total"]
            or 0,
            "taux_remplissage_moyen": StatisticsService._taux_remplissage_moyen(),
            "moyenne_inscriptions_par_evenement": (
                StatisticsService._moyenne_inscriptions()
            ),
            "note_moyenne_globale": EventReview.objects.aggregate(
                moyenne=Avg("note"),
            )["moyenne"]
            or 0,
            "nombre_avis_total": EventReview.objects.count(),
        }

    @staticmethod
    def _taux_remplissage_moyen() -> float:
        """Moyenne, sur tous les événements publiés/terminés ayant une
        capacité définie, du ratio places prises / capacité max."""
        evenements = Event.objects.filter(
            statut__in=[Event.Statut.PUBLISHED, Event.Statut.FINISHED],
            capacite_max__gt=0,
        ).annotate(
            taux=ExpressionWrapper(
                (F("capacite_max") - F("places_restantes")) * 1.0 / F("capacite_max"),
                output_field=FloatField(),
            ),
        )
        resultat = evenements.aggregate(moyenne=Avg("taux"))["moyenne"]
        return round((resultat or 0) * 100, 2)  # en pourcentage

    @staticmethod
    def _moyenne_inscriptions() -> float:
        total_evenements = Event.objects.filter(
            statut__in=[Event.Statut.PUBLISHED, Event.Statut.FINISHED],
        ).count()
        if total_evenements == 0:
            return 0.0
        total_inscriptions = Inscription.objects.filter(
            statut=Inscription.Statut.CONFIRMEE,
        ).count()
        return round(total_inscriptions / total_evenements, 2)

    @staticmethod
    def statistiques_organisateur(organizer) -> dict:
        """Statistiques limitées aux événements d'un organisateur donné."""
        evenements = Event.objects.filter(organizer=organizer)
        paiements_reussis = Payment.objects.filter(
            statut=Payment.Statut.REUSSI,
            inscription__event__organizer=organizer,
        )
        inscriptions_confirmees = Inscription.objects.filter(
            event__organizer=organizer,
            statut=Inscription.Statut.CONFIRMEE,
        )

        return {
            "total_evenements": evenements.count(),
            "evenements_publies": evenements.filter(
                statut=Event.Statut.PUBLISHED,
            ).count(),
            "total_participants": inscriptions_confirmees.count(),
            "revenus_total": paiements_reussis.aggregate(total=Sum("montant"))["total"]
            or 0,
            "note_moyenne": EventReview.objects.filter(
                event__organizer=organizer,
            ).aggregate(moyenne=Avg("note"))["moyenne"]
            or 0,
            "nombre_avis": EventReview.objects.filter(
                event__organizer=organizer,
            ).count(),
        }

    @staticmethod
    def statistiques_evenement(event: Event) -> dict:
        """Détail statistique d'un événement précis."""
        inscriptions_confirmees = Inscription.objects.filter(
            event=event,
            statut=Inscription.Statut.CONFIRMEE,
        )
        paiements_reussis = Payment.objects.filter(
            statut=Payment.Statut.REUSSI,
            inscription__event=event,
        )
        avis = EventReview.objects.filter(event=event)

        taux_remplissage = 0.0
        if event.capacite_max > 0:
            places_prises = event.capacite_max - event.places_restantes
            taux_remplissage = round(
                (places_prises / event.capacite_max) * 100,
                2,
            )

        repartition_notes = {
            row["note"]: row["total"]
            for row in avis.values("note").annotate(total=Count("id"))
        }

        return {
            "capacite_max": event.capacite_max,
            "places_restantes": event.places_restantes,
            "taux_remplissage": taux_remplissage,
            "total_participants": inscriptions_confirmees.count(),
            "revenus": paiements_reussis.aggregate(total=Sum("montant"))["total"] or 0,
            "note_moyenne": avis.aggregate(moyenne=Avg("note"))["moyenne"] or 0,
            "nombre_avis": avis.count(),
            "repartition_notes": {n: repartition_notes.get(n, 0) for n in range(1, 6)},
        }
