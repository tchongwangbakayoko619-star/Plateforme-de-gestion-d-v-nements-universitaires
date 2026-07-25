# gather/payments/providers/__init__.py
from .base import PaymentProvider
from .base import PaymentProviderError
from .campay import CamPayProvider

PROVIDERS: dict[str, type[PaymentProvider]] = {
    "campay": CamPayProvider,
}


def get_provider(nom: str) -> PaymentProvider:
    """Factory : renvoie une instance du fournisseur demandé. Ajouter un
    fournisseur = l'enregistrer ici, rien d'autre à modifier ailleurs."""
    provider_cls = PROVIDERS.get(nom)
    if provider_cls is None:
        message = f"Fournisseur de paiement inconnu : {nom}"
        raise PaymentProviderError(message)
    return provider_cls()
