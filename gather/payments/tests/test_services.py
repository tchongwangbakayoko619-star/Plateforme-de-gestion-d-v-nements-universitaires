# gather/payments/tests/test_services.py
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError

from gather.events.models import Event
from gather.events.tests.factories import creer_event
from gather.events.tests.factories import creer_organizer
from gather.events.tests.factories import creer_student
from gather.inscriptions.models import Inscription
from gather.payments.models import Payment
from gather.payments.services import PaymentService

pytestmark = pytest.mark.django_db

MONTANT_TEST = 5000


def _event_payant():
    organizer = creer_organizer()
    return creer_event(
        organizer,
        statut=Event.Statut.PUBLISHED,
        type_paiement=Event.TypePaiement.PAYANT,
        prix=MONTANT_TEST,
        capacite_max=10,
        places_restantes=10,
    )


def _inscription_directe(event, student):
    """Crée une inscription sans passer par InscriptionService, pour
    isoler le test du paiement (pas de billet auto pour un événement
    payant côté InscriptionService)."""
    return Inscription.objects.create(
        event=event,
        student=student,
        statut=Inscription.Statut.CONFIRMEE,
    )


@patch("gather.payments.services.get_provider")
def test_initier_paiement_cree_payment_en_attente(mock_get_provider):
    mock_get_provider.return_value.initier_paiement.return_value = {
        "reference_externe": "ref-123",
        "payload_brut": {"status": "PENDING"},
    }
    event = _event_payant()
    student = creer_student()
    inscription = _inscription_directe(event, student)

    payment = PaymentService.initier_paiement(inscription, telephone="237670000000")

    assert payment.statut == Payment.Statut.EN_ATTENTE
    assert payment.reference_externe == "ref-123"


@patch("gather.payments.services.get_provider")
def test_confirmer_paiement_genere_billet(mock_get_provider):
    mock_get_provider.return_value.initier_paiement.return_value = {
        "reference_externe": "ref-456",
        "payload_brut": {},
    }
    event = _event_payant()
    student = creer_student()
    inscription = _inscription_directe(event, student)
    payment = PaymentService.initier_paiement(inscription, telephone="237670000000")

    payment = PaymentService.confirmer_paiement("ref-456", Payment.Statut.REUSSI)

    inscription.refresh_from_db()
    assert payment.statut == Payment.Statut.REUSSI
    assert hasattr(inscription, "ticket")


@patch("gather.payments.services.get_provider")
def test_confirmation_idempotente(mock_get_provider):
    mock_get_provider.return_value.initier_paiement.return_value = {
        "reference_externe": "ref-789",
        "payload_brut": {},
    }
    event = _event_payant()
    student = creer_student()
    inscription = _inscription_directe(event, student)
    PaymentService.initier_paiement(inscription, telephone="237670000000")

    PaymentService.confirmer_paiement("ref-789", Payment.Statut.REUSSI)
    ticket_avant = inscription.ticket

    # Deuxième appel (simulateur de webhook dupliqué) — ne doit rien recréer
    PaymentService.confirmer_paiement("ref-789", Payment.Statut.REUSSI)
    inscription.refresh_from_db()

    assert inscription.ticket.id == ticket_avant.id


@patch("gather.payments.services.get_provider")
def test_double_paiement_meme_inscription_interdit(mock_get_provider):
    mock_get_provider.return_value.initier_paiement.return_value = {
        "reference_externe": "ref-999",
        "payload_brut": {},
    }
    event = _event_payant()
    student = creer_student()
    inscription = _inscription_directe(event, student)
    PaymentService.initier_paiement(inscription, telephone="237670000000")

    with pytest.raises(ValidationError):
        PaymentService.initier_paiement(inscription, telephone="237670000000")
