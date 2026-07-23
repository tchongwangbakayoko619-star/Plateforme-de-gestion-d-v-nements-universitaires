# gather/students/services.py
import logging

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import Student

User = get_user_model()
logger = logging.getLogger(__name__)


class StudentService:
    """Logique métier liée au profil académique (Student)."""

    @staticmethod
    def creer_profil(user, **data) -> Student:
        """
        Crée le profil étudiant associé à un user.

        Raises:
            ValidationError: si le user n'a pas le rôle ETUDIANT,
                              ou si un profil existe déjà.
        """
        if not user.is_etudiant:
            message = (
                "Seul un utilisateur avec le rôle ÉTUDIANT peut avoir "
                "un profil Student."
            )
            raise ValidationError(message)

        if hasattr(user, "student_profile"):
            message = f"{user.email} a déjà un profil étudiant."
            raise ValidationError(message)

        matricule = data.get("matricule", "").strip()
        if not matricule:
            message = "Le matricule est requis."
            raise ValidationError(message)

        student = Student(
            user=user,
            matricule=matricule,
            filiere=data.get("filiere", "").strip(),
            departement=data.get("departement", "").strip(),
            niveau_etude=data.get("niveau_etude", "").strip(),
            promotion=data.get("promotion", "").strip(),
            groupe=data.get("groupe", "").strip(),
            date_naissance=data.get("date_naissance"),
            sexe=data.get("sexe", "").strip(),
        )
        student.full_clean()  # déclenche les validators (unicité matricule, etc.)
        student.save()

        logger.info(
            "Profil étudiant créé pour %s (matricule: %s)",
            user.email,
            matricule,
        )
        return student

    @staticmethod
    def modifier_profil(student: Student, **data) -> Student:
        champs_modifiables = [
            "filiere",
            "departement",
            "niveau_etude",
            "promotion",
            "groupe",
            "date_naissance",
            "sexe",
            "statut_academique",
        ]
        for champ in champs_modifiables:
            if champ in data:
                setattr(student, champ, data[champ])

        student.full_clean()
        student.save()
        return student

    @staticmethod
    def get_etudiants(filters: dict | None = None):
        """Requête optimisée avec select_related sur le user associé."""
        queryset = Student.objects.select_related("user").order_by("-user__date_joined")

        if not filters:
            return queryset

        if filters.get("departement"):
            queryset = queryset.filter(departement=filters["departement"])
        if filters.get("statut_academique"):
            queryset = queryset.filter(statut_academique=filters["statut_academique"])
        if filters.get("promotion"):
            queryset = queryset.filter(promotion=filters["promotion"])

        return queryset
