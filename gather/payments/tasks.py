# gather/payments/tasks.py
from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import Payment
from .services import PaymentService

logger = logging.getLogger(__name__)

SECONDES_AVANT_VERIFICATION = 30


@shared_task(
    name="verifier_paiements_en_attente",
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=120,
)
def verifier_paiements_en_attente():
    """Vérifie périodiquement (via Celery Beat) les paiements en attente
    dont la création remonte à plus de 30 secondes — typiquement ceux pour
    lesquels le webhook CamPay n'a pas été reçu (localhost, coupure réseau…).

    Planification recommandée : toutes les 60 secondes.
    """
    seuil = timezone.now() - timedelta(seconds=SECONDES_AVANT_VERIFICATION)
    paiements_en_attente: list[Payment] = list(
        Payment.objects.filter(
            statut=Payment.Statut.EN_ATTENTE,
            created_at__lte=seuil,
        ).select_related("inscription"),
    )

    if not paiements_en_attente:
        return 0

    logger.info(
        "Vérification de %s paiement(s) en attente…",
        len(paiements_en_attente),
    )

    for payment in paiements_en_attente:
        try:
            PaymentService.verifier_statut_manuellement(payment)
            logger.info(
                "Paiement %s vérifié : nouveau statut = %s",
                payment.reference_externe,
                payment.statut,
            )
        except Exception:
            logger.exception(
                "Erreur lors de la vérification du paiement %s",
                payment.reference_externe,
            )

    return len(paiements_en_attente)
