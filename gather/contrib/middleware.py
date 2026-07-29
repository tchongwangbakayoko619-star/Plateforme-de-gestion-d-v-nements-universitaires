# gather/contrib/middleware.py
from __future__ import annotations

import logging
import uuid

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.http import Http404
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse

logger = logging.getLogger(__name__)

# Chemins d'API où l'on garantit une réponse JSON, même en cas d'erreur
# inattendue — les pages HTML classiques restent gérées par Django normalement.
PREFIXES_API = (
    "/events/",
    "/inscriptions/",
    "/payments/",
    "/notifications/",
    "/dashboard/",
    "/statistics/",
)


class ExceptionCentraliseeMiddleware:
    """Garantit qu'une exception non gérée sur une route API renvoie une
    réponse JSON cohérente plutôt qu'une page d'erreur HTML brute, et
    journalise systématiquement avec un identifiant de corrélation."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)

    def _est_route_api(self, request: HttpRequest) -> bool:
        return request.path.startswith(PREFIXES_API)

    def process_exception(self, request: HttpRequest, exception: Exception):
        if not self._est_route_api(request):
            return None  # laisse Django gérer normalement (pages HTML, admin...)

        identifiant_erreur = uuid.uuid4().hex[:12]

        if isinstance(exception, ValidationError):
            message = (
                exception.message
                if hasattr(exception, "message")
                else "; ".join(exception.messages)
            )
            logger.warning(
                "[%s] ValidationError sur %s : %s",
                identifiant_erreur,
                request.path,
                message,
            )
            return JsonResponse(
                {"succes": False, "erreur": message, "reference": identifiant_erreur},
                status=400,
            )

        if isinstance(exception, PermissionDenied):
            logger.warning(
                "[%s] PermissionDenied sur %s",
                identifiant_erreur,
                request.path,
            )
            return JsonResponse(
                {
                    "succes": False,
                    "erreur": "Accès refusé.",
                    "reference": identifiant_erreur,
                },
                status=403,
            )

        if isinstance(exception, Http404):
            return JsonResponse(
                {"succes": False, "erreur": "Ressource introuvable."},
                status=404,
            )

        # Toute autre exception non prévue : log complet avec stacktrace,
        # mais message générique renvoyé au client (jamais de détails
        # internes en production).
        logger.exception(
            "[%s] Erreur non gérée sur %s",
            identifiant_erreur,
            request.path,
        )
        message_client = (
            str(exception) if settings.DEBUG else "Une erreur interne est survenue."
        )
        return JsonResponse(
            {
                "succes": False,
                "erreur": message_client,
                "reference": identifiant_erreur,
            },
            status=500,
        )
