from django.test import TestCase
from django.urls import reverse

HTTP_OK = 200


class HomePageTests(TestCase):
    def test_home_page_renders_without_url_namespace_error(self):
        response = self.client.get(reverse("home"))

        assert response.status_code == HTTP_OK
