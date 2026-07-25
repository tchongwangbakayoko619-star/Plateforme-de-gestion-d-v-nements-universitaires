# gather/notifications/tests/test_services.py
import pytest

from gather.events.tests.factories import creer_student
from gather.notifications.models import Notification
from gather.notifications.services import NotificationService

pytestmark = pytest.mark.django_db

NOMBRE_NOTIFICATIONS_TEST = 3


def test_creer_notification():
    student = creer_student()
    notification = NotificationService.creer(
        destinataire=student.user,
        type_notification=Notification.Type.INSCRIPTION_CONFIRMEE,
        titre="Test",
        message="Message de test",
    )
    assert notification.lu is False
    assert Notification.objects.filter(destinataire=student.user).count() == 1


def test_marquer_comme_lue():
    student = creer_student()
    notification = NotificationService.creer(
        destinataire=student.user,
        type_notification=Notification.Type.INSCRIPTION_CONFIRMEE,
        titre="Test",
        message="Message",
    )
    NotificationService.marquer_comme_lue(notification, student.user)
    notification.refresh_from_db()
    assert notification.lu is True


def test_marquer_toutes_comme_lues():
    student = creer_student()
    for i in range(NOMBRE_NOTIFICATIONS_TEST):
        NotificationService.creer(
            destinataire=student.user,
            type_notification=Notification.Type.INSCRIPTION_CONFIRMEE,
            titre=f"Test {i}",
            message="Message",
        )
    total = NotificationService.marquer_toutes_comme_lues(student.user)
    assert total == NOMBRE_NOTIFICATIONS_TEST
    assert Notification.objects.filter(destinataire=student.user, lu=False).count() == 0


def test_notification_creee_a_l_inscription():
    from gather.events.models import Event  # noqa: PLC0415
    from gather.events.tests.factories import creer_event  # noqa: PLC0415
    from gather.events.tests.factories import creer_organizer  # noqa: PLC0415
    from gather.inscriptions.services import InscriptionService  # noqa: PLC0415

    organizer = creer_organizer()
    student = creer_student()
    event = creer_event(
        organizer,
        statut=Event.Statut.PUBLISHED,
        capacite_max=5,
        places_restantes=5,
    )

    InscriptionService.s_inscrire(student, event)

    assert Notification.objects.filter(
        destinataire=student.user,
        type=Notification.Type.INSCRIPTION_CONFIRMEE,
    ).exists()
