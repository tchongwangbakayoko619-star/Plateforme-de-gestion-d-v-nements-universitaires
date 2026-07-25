from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from gather.inscriptions.models import Inscription

from .services import PaymentService

if TYPE_CHECKING:
    from .models import Payment

logger = logging.getLogger(__name__)


def _erreur_json(exc: Exception, statut: int = 400) -> JsonResponse:
    message = exc.message if hasattr(exc, "message") else str(exc)
    return JsonResponse({"succes": False, "erreur": message}, status=statut)


def _payment_vers_dict(payment: Payment) -> dict:
    return {
        "id": str(payment.id),
        "reference_externe": payment.reference_externe,
        "montant": str(payment.montant),
        "devise": payment.devise,
        "statut": payment.statut,
        "provider": payment.provider,
    }


@login_required
@csrf_protect
@require_http_methods(["POST"])
def initier_paiement(request: HttpRequest, inscription_id: str) -> JsonResponse:
    student = getattr(request.user, "student_profile", None)
    if student is None:
        return JsonResponse(
            {"succes": False, "erreur": "Profil étudiant requis."},
            status=403,
        )

    inscription = get_object_or_404(
        Inscription,
        pk=inscription_id,
        student=student,
    )

    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
        payment = PaymentService.initier_paiement(
            inscription,
            telephone=data.get("telephone", ""),
        )
        return JsonResponse(_payment_vers_dict(payment), status=201)
    except ValidationError as exc:
        return _erreur_json(exc)


def _verifier_signature_webhook(request: HttpRequest) -> bool:
    """Vérifie la signature du webhook via un secret partagé configuré
    côté CamPay (header à adapter selon la config exacte de ton compte
    CamPay — consulte le dashboard pour le nom du header utilisé)."""
    secret = settings.CAMPAY_WEBHOOK_SECRET
    if not secret:
        logger.warning("CAMPAY_WEBHOOK_SECRET non configuré — vérification désactivée.")
        return True  # dev/sandbox uniquement — configurer en prod

    signature_recue = request.headers.get("X-Campay-Signature", "")
    signature_attendue = hmac.new(
        secret.encode("utf-8"),
        request.body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature_recue, signature_attendue)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def webhook_campay(request: HttpRequest) -> HttpResponse:
    """Endpoint appelé par CamPay pour notifier le statut d'une
    transaction. Idempotent : PaymentService.confirmer_paiement()
    ignore les statuts déjà REUSSI."""
    if request.method == "GET":
        return JsonResponse(
            {"succes": True, "message": "Webhook CamPay reachable."},
            status=200,
        )

    if not _verifier_signature_webhook(request):
        logger.warning("Signature de webhook CamPay invalide.")
        return JsonResponse({"succes": False}, status=403)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError, UnicodeDecodeError:
        return JsonResponse({"succes": False, "erreur": "JSON invalide."}, status=400)

    reference = data.get("reference") or data.get("external_reference")
    statut_brut = data.get("status", "PENDING")

    mapping = {"SUCCESSFUL": "reussi", "FAILED": "echoue", "PENDING": "en_attente"}
    statut = mapping.get(statut_brut, "en_attente")

    if not reference:
        return JsonResponse(
            {"succes": False, "erreur": "Référence manquante."},
            status=400,
        )

    try:
        PaymentService.confirmer_paiement(reference, statut, payload_brut=data)
    except ValidationError as exc:
        return _erreur_json(exc)

    return JsonResponse({"succes": True}, status=200)
