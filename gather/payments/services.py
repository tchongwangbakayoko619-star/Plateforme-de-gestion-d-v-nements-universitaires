from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import transaction

from gather.inscriptions.services import TicketService

from .models import Payment
from .models import PaymentTransaction
from .providers import PaymentProviderError
from .providers import get_provider

if TYPE_CHECKING:
    from gather.inscriptions.models import Inscription

logger = logging.getLogger(__name__)


class PaymentService:
    """Toute la logique métier des paiements. Le fournisseur concret
    (CamPay, Stripe...) est injecté via get_provider() — aucune logique
    spécifique à un fournisseur ici."""

    @staticmethod
    @transaction.atomic
    def initier_paiement(
        inscription: Inscription,
        telephone: str,
        provider_nom: str = Payment.Provider.CAMPAY,
    ) -> Payment:
        if hasattr(inscription, "paiement"):
            message = "Un paiement existe déjà pour cette inscription."
            raise ValidationError(message)

        event = inscription.event
        if event.type_paiement != event.TypePaiement.PAYANT:
            message = "Cet événement ne nécessite pas de paiement."
            raise ValidationError(message)

        payment = Payment.objects.create(
            inscription=inscription,
            provider=provider_nom,
            montant=event.prix,
            devise=event.devise,
            telephone=telephone,
            reference_externe=f"tmp-{inscription.id}",  # remplacé ci-dessous
            statut=Payment.Statut.EN_ATTENTE,
        )

        provider = get_provider(provider_nom)
        try:
            resultat = provider.initier_paiement(payment)
        except PaymentProviderError:
            payment.statut = Payment.Statut.ECHOUE
            payment.save(update_fields=["statut"])
            raise

        payment.reference_externe = resultat["reference_externe"]
        payment.save(update_fields=["reference_externe"])

        PaymentTransaction.objects.create(
            payment=payment,
            evenement="initiation",
            payload_brut=resultat.get("payload_brut", {}),
        )

        logger.info(
            "Paiement initié : %s pour inscription %s",
            payment.reference_externe,
            inscription.id,
        )
        return payment

    @staticmethod
    @transaction.atomic
    def confirmer_paiement(
        reference_externe: str,
        nouveau_statut: str,
        payload_brut: dict | None = None,
    ) -> Payment:
        """Idempotent : appelée par le webhook ou par une vérification
        manuelle. Si déjà REUSSI, ne refait rien (évite double billet)."""
        try:
            payment = Payment.objects.select_for_update().get(
                reference_externe=reference_externe,
            )
        except Payment.DoesNotExist:
            message = f"Paiement introuvable : {reference_externe}"
            raise ValidationError(message) from None

        if payment.statut == Payment.Statut.REUSSI:
            return payment  # déjà traité — idempotence

        payment.statut = nouveau_statut
        payment.save(update_fields=["statut"])

        PaymentTransaction.objects.create(
            payment=payment,
            evenement=f"webhook_{nouveau_statut}",
            payload_brut=payload_brut or {},
        )

        if nouveau_statut == Payment.Statut.REUSSI:
            TicketService.generer_billet(payment.inscription)
            logger.info(
                "Paiement confirmé, billet généré : %s",
                payment.reference_externe,
            )
        else:
            logger.warning(
                "Paiement non réussi (%s) : %s",
                nouveau_statut,
                payment.reference_externe,
            )

        return payment

    @staticmethod
    def verifier_statut_manuellement(payment: Payment) -> Payment:
        """Vérification à la demande (polling), en complément du webhook —
        utile si le webhook n'a jamais été reçu."""
        provider = get_provider(payment.provider)
        statut = provider.verifier_statut(payment.reference_externe)
        return PaymentService.confirmer_paiement(payment.reference_externe, statut)
