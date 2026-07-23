# gather/users/tasks.py
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


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def envoyer_email_bienvenue(self, user_id: int) -> None:
    """
    Envoie l'email de bienvenue avec un lien sécurisé de définition de
    mot de passe (jamais le mot de passe en clair), de manière asynchrone.
    """
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning("Utilisateur %s introuvable, email non envoyé.", user_id)
        return

    try:
        # Génère le lien sécurisé de définition de mot de passe
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        chemin_relatif = reverse(
            "account_reset_password_from_key",
            kwargs={"uidb36": uid, "key": token},
        )

        # Construit une URL absolue : indispensable dans un email, car il
        # n'y a pas de request.build_absolute_uri() disponible dans une tâche Celery.
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
            subject="Bienvenue sur Gather Université",
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
        logger.exception("Échec d'envoi de l'email à %s, nouvelle tentative...", user.email)
        raise self.retry(exc=exc) from exc