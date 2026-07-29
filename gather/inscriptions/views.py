# gather/inscriptions/views.py — version complète avec les vues de check-in et billet
from __future__ import annotations

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView

from gather.events.models import Event
from gather.users.mixins import RoleRequiredMixin
from gather.users.models import User

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
def s_inscrire(request: HttpRequest, event_id: str):
    """Gère à la fois les soumissions de formulaire HTML classique
    (redirection avec message) et les appels API attendant du JSON
    (header Accept: application/json)."""
    veut_json = "application/json" in request.headers.get("Accept", "")

    student = getattr(request.user, "student_profile", None)
    if student is None:
        if veut_json:
            return JsonResponse(
                {"succes": False, "erreur": "Profil étudiant requis."},
                status=403,
            )
        messages.error(request, "Seuls les comptes étudiants peuvent s'inscrire.")
        return redirect("events:detail", event_id=event_id)

    event = get_object_or_404(Event, pk=event_id)
    try:
        inscription = InscriptionService.s_inscrire(student, event)
    except ValidationError as exc:
        if veut_json:
            return _erreur_json(exc)
        message = exc.message if hasattr(exc, "message") else str(exc)
        messages.error(request, message)
        return redirect("events:detail", event_id=event_id)

    if veut_json:
        return JsonResponse(_inscription_vers_dict(inscription), status=201)

    if inscription.necessite_paiement:
        messages.info(
            request,
            "Inscription enregistrée ! Veuillez procéder au paiement "
            "pour confirmer votre place.",
        )
    else:
        messages.success(
            request,
            "Inscription confirmée ! Votre billet est disponible.",
        )
    return redirect("events:detail", event_id=event_id)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def annuler_inscription(request: HttpRequest, inscription_id: str):
    veut_json = "application/json" in request.headers.get("Accept", "")
    student = getattr(request.user, "student_profile", None)

    if student is None:
        if veut_json:
            return JsonResponse(
                {"succes": False, "erreur": "Profil étudiant requis."},
                status=403,
            )
        messages.error(
            request,
            "Seuls les comptes étudiants peuvent annuler une inscription.",
        )
        return redirect("events:list")

    inscription = get_object_or_404(Inscription, pk=inscription_id)
    response = None
    try:
        inscription = InscriptionService.annuler_inscription(inscription, student)
        if veut_json:
            response = JsonResponse(_inscription_vers_dict(inscription), status=200)
        else:
            messages.success(request, "Inscription annulée.")
            response = redirect("events:list")
    except InscriptionPermissionError as exc:
        if veut_json:
            response = _erreur_json(exc, statut=403)
        else:
            messages.error(request, str(exc))
            response = redirect("events:list")
    except ValidationError as exc:
        if veut_json:
            response = _erreur_json(exc)
        else:
            message = exc.message if hasattr(exc, "message") else str(exc)
            messages.error(request, message)
            response = redirect("events:list")

    assert response is not None
    return response


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


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CheckInPageView(RoleRequiredMixin, TemplateView):
    """Page de scan caméra pour le check-in à l'entrée d'un événement.

    ensure_csrf_cookie force Django à poser le cookie csrftoken dès le
    chargement de cette page (elle n'a pas de {% csrf_token %} classique
    puisque c'est du JS pur qui envoie le fetch), sinon le header
    X-CSRFToken envoyé par le JS serait vide/invalide.
    """

    template_name = "inscriptions/checkin.html"
    allowed_roles = [User.Role.ORGANISATEUR, User.Role.ADMIN]


checkin_page_view = CheckInPageView.as_view()


class BilletView(LoginRequiredMixin, TemplateView):
    """Billet imprimable : QR code + infos, avec bouton d'impression."""

    template_name = "inscriptions/billet.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        inscription = get_object_or_404(
            Inscription.objects.select_related("event", "student__user", "ticket"),
            pk=self.kwargs["inscription_id"],
        )
        student = getattr(self.request.user, "student_profile", None)
        if student is None or inscription.student_id != student.id:
            message = "Ce billet ne vous appartient pas."
            raise ValidationError(message)

        context["inscription"] = inscription
        context["ticket"] = getattr(inscription, "ticket", None)
        return context


billet_view = BilletView.as_view()
