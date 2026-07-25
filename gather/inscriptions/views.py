# gather/inscriptions/views.py
from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from gather.events.models import Event

from .models import Inscription
from .services import InscriptionPermissionError
from .services import InscriptionService
from .services import TicketService


def _erreur_json(exc: Exception, statut: int = 400) -> JsonResponse:
    message = exc.message if hasattr(exc, "message") else str(exc)
    return JsonResponse({"succes": False, "erreur": message}, status=statut)


def _inscription_vers_dict(inscription: Inscription) -> dict:
    ticket = getattr(inscription, "ticket", None)
    return {
        "id": str(inscription.id),
        "event_id": str(inscription.event_id),
        "event_titre": inscription.event.titre,
        "statut": inscription.statut,
        "date_inscription": inscription.date_inscription.isoformat(),
        "date_annulation": (
            inscription.date_annulation.isoformat()
            if inscription.date_annulation
            else None
        ),
        "ticket": (
            {
                "id": str(ticket.id),
                "code_qr": ticket.code_qr,
                "image_qr": ticket.image_qr.url if ticket.image_qr else None,
                "statut": ticket.statut,
            }
            if ticket
            else None
        ),
    }


@login_required
@csrf_protect
@require_http_methods(["POST"])
def s_inscrire(request: HttpRequest, event_id: str) -> JsonResponse:
    student = getattr(request.user, "student_profile", None)
    if student is None:
        return JsonResponse(
            {"succes": False, "erreur": "Profil étudiant requis."},
            status=403,
        )
    event = get_object_or_404(Event, pk=event_id)
    try:
        inscription = InscriptionService.s_inscrire(student, event)
        return JsonResponse(_inscription_vers_dict(inscription), status=201)
    except ValidationError as exc:
        return _erreur_json(exc)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def annuler_inscription(request: HttpRequest, inscription_id: str) -> JsonResponse:
    student = getattr(request.user, "student_profile", None)
    if student is None:
        return JsonResponse(
            {"succes": False, "erreur": "Profil étudiant requis."},
            status=403,
        )
    inscription = get_object_or_404(Inscription, pk=inscription_id)
    try:
        inscription = InscriptionService.annuler_inscription(inscription, student)
        return JsonResponse(_inscription_vers_dict(inscription), status=200)
    except InscriptionPermissionError as exc:
        return _erreur_json(exc, statut=403)
    except ValidationError as exc:
        return _erreur_json(exc)


@login_required
@require_http_methods(["GET"])
def mes_inscriptions(request: HttpRequest) -> JsonResponse:
    student = getattr(request.user, "student_profile", None)
    if student is None:
        return JsonResponse(
            {"succes": False, "erreur": "Profil étudiant requis."},
            status=403,
        )
    inscriptions = InscriptionService.get_inscriptions_etudiant(student)
    return JsonResponse(
        {"resultats": [_inscription_vers_dict(i) for i in inscriptions]},
        status=200,
    )


@login_required
@require_http_methods(["GET"])
def inscrits_evenement(request: HttpRequest, event_id: str) -> JsonResponse:
    event = get_object_or_404(Event, pk=event_id)
    organizer = getattr(request.user, "organizer_profile", None)
    est_admin = getattr(request.user, "is_administrateur", False)

    if not est_admin and (organizer is None or event.organizer_id != organizer.id):
        return JsonResponse(
            {"succes": False, "erreur": "Accès non autorisé."},
            status=403,
        )

    inscriptions = InscriptionService.get_inscrits_evenement(event)
    return JsonResponse(
        {"resultats": [_inscription_vers_dict(i) for i in inscriptions]},
        status=200,
    )


@login_required
@csrf_protect
@require_http_methods(["POST"])
def check_in(request: HttpRequest) -> JsonResponse:
    organizer = getattr(request.user, "organizer_profile", None)
    est_admin = getattr(request.user, "is_administrateur", False)
    if not est_admin and organizer is None:
        return JsonResponse(
            {"succes": False, "erreur": "Accès non autorisé."},
            status=403,
        )

    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
        code_qr = data.get("code_qr", "")
        resultat = TicketService.valider_qr_code(code_qr)
        return JsonResponse(resultat, status=200)
    except ValidationError as exc:
        return _erreur_json(exc)
