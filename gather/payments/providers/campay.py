# gather/payments/providers/campay.py
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import requests
from django.conf import settings

from .base import PaymentProvider
from .base import PaymentProviderError

if TYPE_CHECKING:
    from gather.payments.models import Payment

logger = logging.getLogger(__name__)

DELAI_REQUETE_SECONDES = 15


class CamPayProvider(PaymentProvider):
    """Intégration CamPay (Mobile Money MTN/Orange, Cameroun).

    Documentation : https://documenter.getpostman.com/view/2391374/T1LV8PVA
    Endpoints utilisés : /token/, /collect/, /transaction/{reference}/
    """

    # Statuts renvoyés par CamPay -> statuts normalisés de Payment.Statut
    MAPPING_STATUTS: dict[str, str] = {
        "SUCCESSFUL": "reussi",
        "FAILED": "echoue",
        "PENDING": "en_attente",
    }

    def __init__(self) -> None:
        self.base_url = settings.CAMPAY_BASE_URL.rstrip("/")
        self.app_username = settings.CAMPAY_APP_USERNAME
        self.app_password = settings.CAMPAY_APP_PASSWORD

    def _obtenir_token(self) -> str:
        try:
            reponse = requests.post(
                f"{self.base_url}/token/",
                json={
                    "username": self.app_username,
                    "password": self.app_password,
                },
                timeout=DELAI_REQUETE_SECONDES,
            )
            reponse.raise_for_status()
        except requests.RequestException as exc:
            logger.exception("Échec d'authentification CamPay.")
            message = "Impossible de s'authentifier auprès de CamPay."
            raise PaymentProviderError(message) from exc

        token = reponse.json().get("token")
        if not token:
            message = "Réponse CamPay invalide : token absent."
            raise PaymentProviderError(message)
        return token

    def initier_paiement(self, payment: Payment) -> dict:
        token = self._obtenir_token()
        headers = {"Authorization": f"Token {token}"}
        corps = {
            "amount": str(int(payment.montant)),
            "currency": payment.devise,
            "from": payment.telephone,
            "description": f"Inscription événement — {payment.inscription.event.titre}",
            "external_reference": str(payment.id),
        }

        try:
            reponse = requests.post(
                f"{self.base_url}/collect/",
                json=corps,
                headers=headers,
                timeout=DELAI_REQUETE_SECONDES,
            )
            reponse.raise_for_status()
        except requests.RequestException as exc:
            logger.exception("Échec de la demande de paiement CamPay.")
            message = "Impossible de contacter CamPay pour ce paiement."
            raise PaymentProviderError(message) from exc

        data = reponse.json()
        reference = data.get("reference")
        if not reference:
            message = "Réponse CamPay invalide : référence absente."
            raise PaymentProviderError(message)

        return {"reference_externe": reference, "payload_brut": data}

    def verifier_statut(self, reference_externe: str) -> str:
        token = self._obtenir_token()
        headers = {"Authorization": f"Token {token}"}

        try:
            reponse = requests.get(
                f"{self.base_url}/transaction/{reference_externe}/",
                headers=headers,
                timeout=DELAI_REQUETE_SECONDES,
            )
            reponse.raise_for_status()
        except requests.RequestException as exc:
            logger.exception("Échec de vérification du statut CamPay.")
            message = "Impossible de vérifier le statut auprès de CamPay."
            raise PaymentProviderError(message) from exc

        statut_campay = reponse.json().get("status", "PENDING")
        return self.MAPPING_STATUTS.get(statut_campay, "en_attente")
