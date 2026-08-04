# gather/notifications/services.py
from __future__ import annotations

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.exceptions import ValidationError

from .models import Notification

logger = logging.getLogger(__name__)


class NotificationService:
    """Toute la création de notifications passe par ici. Chaque
    notification créée est aussi poussée en temps réel via WebSocket
    au groupe de canal de l'utilisateur, si celui-ci est connecté."""

    @staticmethod
    def _groupe_utilisateur(user_id: int | str) -> str:
        return f"notifications_user_{user_id}"

    @classmethod
    def creer(
        cls,
        destinataire,
        type_notification: str,
        titre: str,
        message: str,
        lien: str = "",
    ) -> Notification:
        notification = Notification.objects.create(
            destinataire=destinataire,
            type=type_notification,
            titre=titre,
            message=message,
            lien=lien,
        )
        cls._pousser_temps_reel(notification)
        logger.info(
            "Notification créée : %s -> %s",
            destinataire.email,
            type_notification,
        )
        return notification

    @classmethod
    def _pousser_temps_reel(cls, notification: Notification) -> None:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        try:
            async_to_sync(channel_layer.group_send)(
                cls._groupe_utilisateur(notification.destinataire_id),
                {
                    "type": "notification.message",
                    "notification": {
                        "id": str(notification.id),
                        "type": notification.type,
                        "titre": notification.titre,
                        "message": notification.message,
                        "lien": notification.lien,
                        "lu": notification.lu,
                        "created_at": notification.created_at.isoformat(),
                    },
                },
            )
        except Exception:  # noqa: BLE001
            # Le WebSocket est un confort, pas une garantie — la
            # notification reste consultable en base même si l'envoi
            # temps réel échoue (utilisateur non connecté, Redis down...).
            # On catch large ici volontairement : channels/asgiref peuvent
            # lever plusieurs types d'exceptions selon le backend du
            # channel layer (Redis, in-memory...), et aucune ne doit faire
            # échouer la création de la notification elle-même.
            logger.warning(
                "Échec de l'envoi WebSocket pour la notification %s",
                notification.id,
            )

    @staticmethod
    def marquer_comme_lue(notification: Notification, user) -> Notification:
        if notification.destinataire_id != user.id:
            message = "Vous ne pouvez marquer que vos propres notifications."
            raise ValidationError(message)
        if not notification.lu:
            notification.lu = True
            notification.save(update_fields=["lu"])
        return notification

    @staticmethod
    def marquer_toutes_comme_lues(user) -> int:
        return Notification.objects.filter(destinataire=user, lu=False).update(lu=True)

    @staticmethod
    def supprimer(notification: Notification, user) -> None:
        if notification.destinataire_id != user.id:
            message = "Vous ne pouvez supprimer que vos propres notifications."
            raise ValidationError(message)
        notification.delete()

    @staticmethod
    def get_notifications(user, *, non_lues_uniquement: bool = False):
        queryset = Notification.objects.filter(destinataire=user)
        if non_lues_uniquement:
            queryset = queryset.filter(lu=False)
        return queryset
