# gather/payments/providers/base.py
from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gather.payments.models import Payment


class PaymentProviderError(Exception):
    """Levée quand l'appel au fournisseur de paiement échoue."""


class PaymentProvider(ABC):
    """Interface commune à tous les fournisseurs de paiement. Ajouter un
    nouveau fournisseur (Stripe, CinetPay, Flutterwave) ne nécessite que
    d'implémenter cette interface — aucun autre code à modifier."""

    @abstractmethod
    def initier_paiement(self, payment: Payment) -> dict:
        """Déclenche la demande de paiement chez le fournisseur.
        Retourne un dict contenant au minimum {"reference_externe": str}."""

    @abstractmethod
    def verifier_statut(self, reference_externe: str) -> str:
        """Interroge le fournisseur et retourne un statut normalisé parmi
        Payment.Statut (reussi / echoue / en_attente)."""
