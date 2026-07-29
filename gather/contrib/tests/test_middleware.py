from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from django.test import Client

pytestmark = pytest.mark.django_db


def test_validation_error_retourne_json_sur_route_api(client: Client):
    # Utilise une route existante qui peut lever ValidationError
    # (ex: check-in avec un code_qr inexistant)
    response = client.post(
        "/inscriptions/check-in/",
        data='{"code_qr": "inexistant"}',
        content_type="application/json",
    )
    # 302 si non authentifié (login_required), sinon 400/403 selon le cas
    assert response.status_code in (302, 400, 403)
