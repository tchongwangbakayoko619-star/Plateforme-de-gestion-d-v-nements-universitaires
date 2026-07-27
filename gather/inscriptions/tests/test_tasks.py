import datetime

import pytest
from django.core import mail
from django.utils import timezone

from gather.events.models import Event
from gather.events.tests.factories import creer_event
from gather.events.tests.factories import creer_organizer
from gather.events.tests.factories import creer_student
from gather.inscriptions.services import InscriptionService
from gather.inscriptions.tasks import envoyer_rappels_24h

pytestmark = pytest.mark.django_db


def test_envoyer_rappels_24h():
    organizer = creer_organizer()
    student = creer_student()
    event = creer_event(
        organizer,
        statut=Event.Statut.PUBLISHED,
        date_debut=timezone.now() + datetime.timedelta(hours=24, minutes=5),
        date_fin=timezone.now() + datetime.timedelta(hours=26),
        capacite_max=10,
        places_restantes=10,
    )
    InscriptionService.s_inscrire(student, event)
    mail.outbox.clear()

    resultat = envoyer_rappels_24h()

    assert resultat["total_rappels"] == 1
    assert len(mail.outbox) == 1
    assert "demain" in mail.outbox[0].subject.lower()
