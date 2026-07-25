# gather/notifications/views.py
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from .models import Notification
from .services import NotificationService


def _erreur_json(exc: Exception, statut: int = 400) -> JsonResponse:
    message = exc.message if hasattr(exc, "message") else str(exc)
    return JsonResponse({"succes": False, "erreur": message}, status=statut)


def _notification_vers_dict(notification: Notification) -> dict:
    return {
        "id": str(notification.id),
        "type": notification.type,
        "titre": notification.titre,
        "message": notification.message,
        "lien": notification.lien,
        "lu": notification.lu,
        "created_at": notification.created_at.isoformat(),
    }


@login_required
@require_http_methods(["GET"])
def liste_notifications(request: HttpRequest) -> JsonResponse:
    non_lues = request.GET.get("non_lues") == "true"
    notifications = NotificationService.get_notifications(
        request.user,
        non_lues_uniquement=non_lues,
    )
    return JsonResponse(
        {
            "resultats": [_notification_vers_dict(n) for n in notifications],
            "non_lues_count": Notification.objects.filter(
                destinataire=request.user,
                lu=False,
            ).count(),
        },
        status=200,
    )


@login_required
@csrf_protect
@require_http_methods(["POST"])
def marquer_comme_lue(request: HttpRequest, notification_id: str) -> JsonResponse:
    notification = get_object_or_404(Notification, pk=notification_id)
    try:
        notification = NotificationService.marquer_comme_lue(notification, request.user)
        return JsonResponse(_notification_vers_dict(notification), status=200)
    except ValidationError as exc:
        return _erreur_json(exc, statut=403)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def marquer_toutes_comme_lues(request: HttpRequest) -> JsonResponse:
    total = NotificationService.marquer_toutes_comme_lues(request.user)
    return JsonResponse({"succes": True, "total_marquees": total}, status=200)


@login_required
@csrf_protect
@require_http_methods(["DELETE"])
def supprimer_notification(request: HttpRequest, notification_id: str) -> JsonResponse:
    notification = get_object_or_404(Notification, pk=notification_id)
    try:
        NotificationService.supprimer(notification, request.user)
        return JsonResponse({"succes": True}, status=200)
    except ValidationError as exc:
        return _erreur_json(exc, statut=403)
