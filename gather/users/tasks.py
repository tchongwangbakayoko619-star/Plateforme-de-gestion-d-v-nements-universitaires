# gather/users/tasks.py
import io
import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    rate_limit="10/m",
)
def envoyer_email_bienvenue(self, user_id: int) -> None:
    """
    Envoie l'email de bienvenue avec un lien sécurisé de définition de
    mot de passe (jamais le mot de passe en clair), de manière asynchrone.

    rate_limit="10/m" : au plus 10 envois par minute, pour éviter que
    plusieurs connexions SMTP simultanées vers Gmail ne provoquent des
    timeouts (observé lors d'un import CSV avec plusieurs utilisateurs
    créés en même temps).
    """
    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=user_id)
    except user_model.DoesNotExist:
        logger.warning("Utilisateur %s introuvable, email non envoyé.", user_id)
        return

    try:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        chemin_relatif = reverse(
            "account_reset_password_from_key",
            kwargs={"uidb36": uid, "key": token},
        )

        # URL absolue obligatoire dans un email : pas de request disponible
        # dans une tâche Celery pour utiliser build_absolute_uri().
        current_site = Site.objects.get_current()
        protocole = "http" if settings.DEBUG else "https"
        lien_definition_mdp = f"{protocole}://{current_site.domain}{chemin_relatif}"

        context = {
            "user_first_name": user.first_name,
            "user_email": user.email,
            "user_role_display": user.get_role_display(),
            "lien_definition_mdp": lien_definition_mdp,
        }
        html_message = render_to_string("emails/welcome.html", context)

        send_mail(
            subject="Bienvenue sur EventHub Université",
            message=(
                f"Bonjour {user.get_full_name()},\n\n"
                f"Votre compte a été créé.\n"
                f"Email : {user.email}\n\n"
                f"Définissez votre mot de passe ici : {lien_definition_mdp}\n"
            ),
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info("Email de bienvenue envoyé à %s", user.email)

    except Exception as exc:
        logger.exception(
            "Échec d'envoi de l'email à %s, nouvelle tentative...",
            user.email,
        )
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def importer_utilisateurs_depuis_csv(
    self,
    csv_content: str,
    admin_user_id: int,
) -> dict:
    """
    Exécute l'import CSV en arrière-plan, sans bloquer la requête HTTP de
    l'admin. Chaque utilisateur créé déclenche déjà sa propre tâche
    d'email de bienvenue (via AdminUserService). À la fin, un rapport
    récapitulatif est envoyé à l'admin ayant lancé l'import.
    """
    # Import différé : évite l'import circulaire avec services.py,
    # qui importe lui-même envoyer_email_bienvenue depuis ce module.
    from gather.users.services import AdminUserService  # noqa: PLC0415

    user_model = get_user_model()
    try:
        admin_user = user_model.objects.get(pk=admin_user_id)
    except user_model.DoesNotExist:
        logger.exception("Admin %s introuvable, import CSV annulé.", admin_user_id)
        return {"error": "admin_introuvable"}

    csv_file = io.BytesIO(csv_content.encode("utf-8"))
    results = AdminUserService.import_from_csv(csv_file, admin_user)

    _envoyer_rapport_import(admin_user, results)
    return results


def _envoyer_rapport_import(admin_user, results: dict) -> None:
    """Envoie un email HTML récapitulatif de l'import CSV à l'admin."""
    nb_crees = len(results["created"])
    nb_erreurs = len(results["errors"])

    current_site = Site.objects.get_current()
    protocole = "http" if settings.DEBUG else "https"
    lien_liste_utilisateurs = f"{protocole}://{current_site.domain}/users/admin/liste/"

    context = {
        "admin_first_name": admin_user.first_name,
        "nb_crees": nb_crees,
        "nb_erreurs": nb_erreurs,
        "utilisateurs_crees": results["created"],
        "erreurs": results["errors"],
        "lien_liste_utilisateurs": lien_liste_utilisateurs,
    }
    html_message = render_to_string("emails/rapport_import.html", context)

    # Version texte simple, requise en fallback pour les clients mail
    # qui n'affichent pas le HTML.
    lignes_erreurs = "\n".join(
        f"- Ligne {e.get('row')} ({e.get('email', 'inconnu')}) : "
        f"{e.get('error') or e.get('message')}"
        for e in results["errors"]
    )
    message = (
        f"Bonjour {admin_user.first_name},\n\n"
        f"L'import CSV est terminé.\n"
        f"Utilisateurs créés : {nb_crees}\n"
        f"Erreurs : {nb_erreurs}\n\n"
        f"{lignes_erreurs if lignes_erreurs else 'Aucune erreur.'}\n"
    )

    try:
        send_mail(
            subject="Rapport d'import CSV — EventHub Université",
            message=message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin_user.email],
            fail_silently=False,
        )
        logger.info("Rapport d'import envoyé à %s", admin_user.email)
    except Exception:
        logger.exception("Échec d'envoi du rapport d'import à %s", admin_user.email)
        raise
