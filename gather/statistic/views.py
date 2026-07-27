# gather/statistics/views.py
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from gather.events.models import Event

from .services import StatisticsService


@login_required
def statistiques_globales(request: HttpRequest) -> JsonResponse:
    if not getattr(request.user, "is_administrateur", False):
        return JsonResponse(
            {"succes": False, "erreur": "Accès administrateur requis."},
            status=403,
        )
    return JsonResponse(StatisticsService.statistiques_globales(), status=200)


@login_required
def statistiques_organisateur(request: HttpRequest) -> JsonResponse:
    organizer = getattr(request.user, "organizer_profile", None)
    if organizer is None:
        return JsonResponse(
            {"succes": False, "erreur": "Profil organisateur requis."},
            status=403,
        )
    return JsonResponse(
        StatisticsService.statistiques_organisateur(organizer),
        status=200,
    )


@login_required
def statistiques_evenement(request: HttpRequest, event_id: str) -> JsonResponse:
    event = get_object_or_404(Event, pk=event_id)
    organizer = getattr(request.user, "organizer_profile", None)
    est_admin = getattr(request.user, "is_administrateur", False)

    if not est_admin and (organizer is None or event.organizer_id != organizer.id):
        return JsonResponse(
            {"succes": False, "erreur": "Accès non autorisé."},
            status=403,
        )

    return JsonResponse(StatisticsService.statistiques_evenement(event), status=200)
