# gather/users/services.py
import csv
import io
import logging

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError
from django.db import transaction
from django.db.models import Q
from django.utils.crypto import get_random_string

from gather.organizers.services import OrganizerService
from gather.students.services import StudentService
from gather.users.tasks import envoyer_email_bienvenue

User = get_user_model()
logger = logging.getLogger(__name__)

ROLE_MAPPING = {
    "etudiant": User.Role.ETUDIANT,
    "student": User.Role.ETUDIANT,
    "étudiant": User.Role.ETUDIANT,
    "organisateur": User.Role.ORGANISATEUR,
    "organizer": User.Role.ORGANISATEUR,
    "admin": User.Role.ADMIN,
    "administrateur": User.Role.ADMIN,
}


class PermissionDeniedError(ValidationError):
    """Levée quand l'appelant n'a pas les droits nécessaires."""


class UserService:
    """Opérations de base sur User (auth), sans logique de profil métier."""

    @staticmethod
    def check_is_admin(admin_user) -> None:
        if not getattr(admin_user, "is_administrateur", False):
            message = "Seul un administrateur peut effectuer cette action."
            raise PermissionDeniedError(message)

    @staticmethod
    def creer_utilisateur(
        *,
        email: str,
        first_name: str,
        last_name: str,
        role: str,
    ) -> tuple[User, str]:
        """
        Crée uniquement le User (auth). Retourne (user, mot_de_passe_temporaire).
        Ne connaît rien de Student/Organizer — responsabilité déléguée
        à l'orchestrateur.
        """
        email = email.strip().lower()
        if not email:
            message = "L'email est requis."
            raise ValidationError(message)
        validate_email(email)

        if not first_name.strip() or not last_name.strip():
            message = "Le prénom et le nom sont requis."
            raise ValidationError(message)

        if role not in dict(User.Role.choices):
            message = f"Rôle invalide : {role}"
            raise ValidationError(message)

        password = get_random_string(length=12)
        try:
            user = User.objects.create_user(
                email=email,
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                password=password,
                role=role,
                is_active=True,
            )
        except IntegrityError as exc:
            message = f"L'utilisateur {email} existe déjà."
            raise ValidationError(message) from exc

        return user, password

    @staticmethod
    def get_users(filters: dict | None = None):
        queryset = (
            User.objects.all()
            .select_related("student_profile", "organizer_profile")
            .order_by("-date_joined")
        )
        if not filters:
            return queryset

        if filters.get("role"):
            queryset = queryset.filter(role=filters["role"])
        if "is_active" in filters:
            queryset = queryset.filter(is_active=filters["is_active"])
        if filters.get("search"):
            search = filters["search"]
            queryset = queryset.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search),
            )
        return queryset

    @staticmethod
    def supprimer_utilisateur(user, admin_user) -> bool:
        UserService.check_is_admin(admin_user)
        if user == admin_user:
            message = "Vous ne pouvez pas supprimer votre propre compte."
            raise ValidationError(message)
        email = user.email
        user.delete()
        logger.info("Admin %s a supprimé l'utilisateur %s", admin_user.email, email)
        return True


class AdminUserService:
    """
    Couche d'orchestration : combine UserService + StudentService/OrganizerService
    dans une transaction atomique. C'est le SEUL endroit qui connaît les trois apps.
    """

    @staticmethod
    @transaction.atomic
    def creer_utilisateur_avec_profil(data: dict, admin_user) -> User:
        UserService.check_is_admin(admin_user)

        role = data.get("role", User.Role.ETUDIANT)

        user, _password = UserService.creer_utilisateur(
            email=data.get("email", ""),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            role=role,
        )

        if role == User.Role.ETUDIANT:
            StudentService.creer_profil(user, **data)
        elif role == User.Role.ORGANISATEUR:
            OrganizerService.creer_profil(user, **data)
        # ADMIN : aucun profil supplémentaire nécessaire

        logger.info(
            "Admin %s a créé l'utilisateur %s (rôle: %s)",
            admin_user.email,
            user.email,
            role,
        )

        # Email de bienvenue envoyé de manière asynchrone, uniquement si
        # la transaction complète (User + profil) réussit réellement.
        transaction.on_commit(
            lambda: envoyer_email_bienvenue.delay(user.id),
        )

        return user

    @staticmethod
    def import_from_csv(csv_file, admin_user) -> dict:
        """
        Traite le CSV ligne par ligne de façon synchrone. Appelée soit
        directement (petits fichiers), soit depuis la tâche Celery
        importer_utilisateurs_depuis_csv (imports volumineux, en arrière-plan).
        """
        UserService.check_is_admin(admin_user)

        results = {"total": 0, "created": [], "errors": []}
        csv_content = csv_file.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(csv_content))

        required = ["email", "first_name", "last_name", "role"]
        missing = [f for f in required if f not in (reader.fieldnames or [])]
        if missing:
            results["errors"].append(
                {"row": 0, "message": f"Colonnes manquantes : {', '.join(missing)}"},
            )
            return results

        for row_num, row in enumerate(reader, start=2):
            results["total"] += 1
            role_raw = row.get("role", "").strip().lower()

            if role_raw not in ROLE_MAPPING:
                results["errors"].append(
                    {
                        "row": row_num,
                        "email": row.get("email"),
                        "error": f"Rôle inconnu : {role_raw}",
                    },
                )
                continue

            try:
                user = AdminUserService.creer_utilisateur_avec_profil(
                    {**row, "role": ROLE_MAPPING[role_raw]},
                    admin_user,
                )
                results["created"].append({"email": user.email, "row": row_num})
            except ValidationError as e:
                results["errors"].append(
                    {"row": row_num, "email": row.get("email"), "error": str(e)},
                )

        return results
