from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Student(models.Model):
    """Profil académique — uniquement pour les utilisateurs role=ETUDIANT.

    Référence AUTH_USER_MODEL (et non User directement) pour éviter
    tout couplage fort/import circulaire avec l'app users.
    """

    class Sexe(models.TextChoices):
        MASCULIN = "M", _("Masculin")
        FEMININ = "F", _("Féminin")

    class StatutAcademique(models.TextChoices):
        ACTIF = "actif", _("Actif")
        SUSPENDU = "suspendu", _("Suspendu")
        DIPLOME = "diplome", _("Diplômé")
        ABANDON = "abandon", _("Abandon")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )
    matricule = models.CharField(
        _("Matricule"),
        max_length=30,
        unique=True,
        db_index=True,
    )
    filiere = models.CharField(_("Filière"), max_length=150)
    departement = models.CharField(_("Département"), max_length=150, db_index=True)
    niveau_etude = models.CharField(_("Niveau d'étude"), max_length=20)
    promotion = models.CharField(
        _("Promotion"),
        max_length=9,
        help_text=_("Ex: 2025-2026"),
    )
    groupe = models.CharField(_("Groupe / Classe"), max_length=50, blank=True)
    date_naissance = models.DateField(_("Date de naissance"), null=True, blank=True)
    sexe = models.CharField(_("Sexe"), max_length=1, choices=Sexe.choices, blank=True)
    statut_academique = models.CharField(
        _("Statut académique"),
        max_length=20,
        choices=StatutAcademique.choices,
        default=StatutAcademique.ACTIF,
        db_index=True,
    )
    photo_carte_etudiante = models.ImageField(
        _("Photo carte étudiante"),
        upload_to="students/cartes/%Y/",
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = _("Profil étudiant")
        verbose_name_plural = _("Profils étudiants")
        indexes = [
            models.Index(fields=["departement", "promotion"]),
        ]

    def __str__(self) -> str:
        return f"{self.matricule} — {self.user.get_full_name()}"
