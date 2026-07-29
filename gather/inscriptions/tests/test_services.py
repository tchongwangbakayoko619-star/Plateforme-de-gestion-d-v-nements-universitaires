import pytest
from django.core.exceptions import ValidationError

from gather.events.models import Event
from gather.events.tests.factories import creer_event
from gather.events.tests.factories import creer_organizer
from gather.events.tests.factories import creer_student
from gather.inscriptions.models import Inscription
from gather.inscriptions.services import InscriptionService
from gather.inscriptions.services import TicketService

pytestmark = pytest.mark.django_db

CAPACITE_INITIALE_DIX = 10
CAPACITE_INITIALE_CINQ = 5


def _event_publie(**kwargs):
    organizer = creer_organizer()
    return creer_event(organizer, statut=Event.Statut.PUBLISHED, **kwargs)


def test_inscription_evenement_gratuit_genere_billet():
    event = _event_publie(
        capacite_max=CAPACITE_INITIALE_DIX,
        places_restantes=CAPACITE_INITIALE_DIX,
    )
    student = creer_student()

    inscription = InscriptionService.s_inscrire(student, event)

    event.refresh_from_db()
    assert inscription.statut == Inscription.Statut.CONFIRMEE
    assert event.places_restantes == CAPACITE_INITIALE_DIX - 1
    assert hasattr(inscription, "ticket")


def test_double_inscription_interdite():
    event = _event_publie(
        capacite_max=CAPACITE_INITIALE_DIX,
        places_restantes=CAPACITE_INITIALE_DIX,
    )
    student = creer_student()
    InscriptionService.s_inscrire(student, event)

    with pytest.raises(ValidationError):
        InscriptionService.s_inscrire(student, event)


def test_inscription_impossible_si_complet():
    event = _event_publie(capacite_max=1, places_restantes=0)
    student = creer_student()

    with pytest.raises(ValidationError):
        InscriptionService.s_inscrire(student, event)


def test_annulation_libere_une_place():
    event = _event_publie(
        capacite_max=CAPACITE_INITIALE_CINQ,
        places_restantes=CAPACITE_INITIALE_CINQ,
    )
    student = creer_student()
    inscription = InscriptionService.s_inscrire(student, event)

    InscriptionService.annuler_inscription(inscription, student)

    event.refresh_from_db()
    inscription.refresh_from_db()
    assert event.places_restantes == CAPACITE_INITIALE_CINQ
    assert inscription.statut == Inscription.Statut.ANNULEE


def test_annulation_inscription_paiement_en_attente_ne_decr_en_pas_la_place():
    event = _event_publie(
        capacite_max=CAPACITE_INITIALE_CINQ,
        places_restantes=CAPACITE_INITIALE_CINQ,
        type_paiement=Event.TypePaiement.PAYANT,
        prix=1000,
    )
    student = creer_student()
    inscription = InscriptionService.s_inscrire(student, event)

    assert inscription.statut == Inscription.Statut.EN_ATTENTE_PAIEMENT
    assert event.places_restantes == CAPACITE_INITIALE_CINQ

    InscriptionService.annuler_inscription(inscription, student)

    event.refresh_from_db()
    inscription.refresh_from_db()
    assert event.places_restantes == CAPACITE_INITIALE_CINQ
    assert inscription.statut == Inscription.Statut.ANNULEE


def test_check_in_valide_une_seule_fois():
    event = _event_publie(
        capacite_max=CAPACITE_INITIALE_CINQ,
        places_restantes=CAPACITE_INITIALE_CINQ,
    )
    student = creer_student()
    inscription = InscriptionService.s_inscrire(student, event)
    ticket = inscription.ticket

    resultat = TicketService.valider_qr_code(ticket.code_qr)
    assert resultat["statut"] == "utilise"

    with pytest.raises(ValidationError):
        TicketService.valider_qr_code(ticket.code_qr)
