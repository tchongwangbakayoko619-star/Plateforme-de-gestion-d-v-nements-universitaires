from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import CharField
from django.db.models import EmailField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .managers import UserManager

phone_validator = RegexValidator(
    regex=r"^\+?[0-9\s\-]{8,20}$",
    message=_("Format de téléphone invalide."),
)


class User(AbstractUser):
    """
    Modèle utilisateur commun à tous les acteurs authentifiés.

    Ne contient que les données d'authentification et de préférences
    générales. Les profils métier (Student, Organizer) vivent dans
    leurs propres apps et référencent ce modèle via AUTH_USER_MODEL.
    """

    class Role(models.TextChoices):
        ETUDIANT = "etudiant", _("Étudiant")
        ORGANISATEUR = "organisateur", _("Organisateur")
        ADMIN = "admin", _("Administrateur")

    email = EmailField(_("Adresse email"), unique=True, db_index=True)
    username = None  # type: ignore[assignment]

    first_name = CharField(_("Prénom"), max_length=150, blank=True)
    last_name = CharField(_("Nom"), max_length=150, blank=True)

    role = CharField(
        _("Rôle"),
        max_length=20,
        choices=Role.choices,
        default=Role.ETUDIANT,
        db_index=True,
    )

    telephone = CharField(
        _("Téléphone"),
        max_length=20,
        blank=True,
        validators=[phone_validator],
    )
    photo = models.ImageField(
        _("Photo de profil"),
        upload_to="users/photos/%Y/%m/",
        blank=True,
        null=True,
    )
    langue = CharField(
        _("Langue préférée"),
        max_length=10,
        choices=[("fr", _("Français")), ("en", _("English"))],
        default="fr",
    )
    fuseau_horaire = CharField(
        _("Fuseau horaire"),
        max_length=50,
        default="Africa/Douala",
    )
    updated_at = models.DateTimeField(_("Dernière modification"), auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    objects: ClassVar[UserManager] = UserManager()

    class Meta:
        verbose_name = _("Utilisateur")
        verbose_name_plural = _("Utilisateurs")
        indexes = [
            models.Index(fields=["role", "is_active"]),
        ]

    def get_absolute_url(self) -> str:
        return reverse("users:detail", kwargs={"pk": self.id})

    def __str__(self) -> str:
        return f"{self.get_full_name()} ({self.email})"

    @property
    def is_etudiant(self) -> bool:
        return self.role == self.Role.ETUDIANT

    @property
    def is_organisateur(self) -> bool:
        return self.role == self.Role.ORGANISATEUR

    @property
    def is_administrateur(self) -> bool:
        return self.role == self.Role.ADMIN
