from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from gather.users.tasks import _envoyer_rapport_import
from gather.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_envoyer_rapport_import_raises_when_email_backend_fails():
    admin_user = UserFactory.create(email="admin@example.com", first_name="Admin")
    results = {"created": [], "errors": []}

    with (
        patch(
            "gather.users.tasks.Site.objects.get_current",
            return_value=SimpleNamespace(domain="example.com"),
        ),
        patch(
            "gather.users.tasks.render_to_string",
            return_value="<html>rapport</html>",
        ),
        patch("gather.users.tasks.send_mail", side_effect=RuntimeError("smtp issue")),
        pytest.raises(RuntimeError, match="smtp issue"),
    ):
        _envoyer_rapport_import(admin_user, results)
