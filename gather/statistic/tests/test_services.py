# gather/statistics/tests/test_services.py
import pytest

from gather.events.models import Event
from gather.events.tests.factories import creer_event
from gather.events.tests.factories import creer_organizer
from gather.events.tests.factories import creer_student
from gather.inscriptions.services import InscriptionService
from gather.statistic.services import StatisticsService

pytestmark = pytest.mark.django_db

CAPACITE_TEST = 10
INSCRITS_TEST = 4
TAUX_REMPLISSAGE_ATTENDU = 10.0


def test_statistiques_evenement_taux_remplissage():
    organizer = creer_organizer()
    student = creer_student()
    event = creer_event(
        organizer,
        statut=Event.Statut.PUBLISHED,
        capacite_max=CAPACITE_TEST,
        places_restantes=CAPACITE_TEST,
    )

    InscriptionService.s_inscrire(student, event)
    event.refresh_from_db()

    stats = StatisticsService.statistiques_evenement(event)
    assert stats["total_participants"] == 1
    assert stats["taux_remplissage"] == TAUX_REMPLISSAGE_ATTENDU


def test_statistiques_organisateur_isolees():
    organizer_a = creer_organizer()
    organizer_b = creer_organizer()
    creer_event(organizer_a, statut=Event.Statut.PUBLISHED)
    creer_event(organizer_b, statut=Event.Statut.PUBLISHED)

    stats_a = StatisticsService.statistiques_organisateur(organizer_a)
    assert stats_a["total_evenements"] == 1


def test_statistiques_globales_sans_donnees():
    stats = StatisticsService.statistiques_globales()
    assert stats["revenus_total"] == 0
    assert stats["note_moyenne_globale"] == 0
