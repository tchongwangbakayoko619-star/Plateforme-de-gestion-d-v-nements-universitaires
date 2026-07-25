# gather/events/tests.py
from django.test import SimpleTestCase

from gather.events import services


class EventSignalsTests(SimpleTestCase):
    def test_services_can_import_signal(self):
        assert hasattr(services, "EventService")
