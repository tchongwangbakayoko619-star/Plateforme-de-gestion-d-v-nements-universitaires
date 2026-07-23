from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class Organizer(models.Model):
    """Profil associatif — uniquement pour les utilisateurs role=ORGANISATEUR."""

    class Poste(models.TextChoices):
        PRESIDENT = "president", _("Président")
        VICE_PRESIDENT = "vice_president", _("Vice-président")
        SECRETAIRE = "secretaire", _("Secrétaire")
        TRESORIER = "tresorier", _("Trésorier")
        MEMBRE = "membre", _("Membre")

    class Statut(models.TextChoices):
        ACTIF = "actif", _("Actif")
        INACTIF = "inactif", _("Inactif")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organizer_profile",
    )
    club = models.CharField(_("Club / Association"), max_length=255)
    departement = models.CharField(_("Département"), max_length=150, blank=True)
    poste = models.CharField(_("Poste"), max_length=20, choices=Poste.choices)
    date_debut_mandat = models.DateField(_("Date de prise de fonction"))
    date_fin_mandat = models.DateField(
        _("Date de fin de mandat"),
        null=True,
        blank=True,
    )
    bureau_local = models.CharField(_("Bureau / Local"), max_length=100, blank=True)
    biographie = models.TextField(_("Biographie"), blank=True)
    signature_electronique = models.ImageField(
        _("Signature électronique"),
        upload_to="organizers/signatures/%Y/",
        blank=True,
        null=True,
    )
    statut = models.CharField(
        _("Statut"),
        max_length=20,
        choices=Statut.choices,
        default=Statut.ACTIF,
    )

    class Meta:
        verbose_name = _("Profil organisateur")
        verbose_name_plural = _("Profils organisateurs")
        indexes = [
            models.Index(fields=["club", "statut"]),
        ]

    def __str__(self) -> str:
        poste_display = self.get_poste_display()
        user_full_name = self.user.get_full_name()
        return f"{poste_display} — {self.club} ({user_full_name})"

    def clean(self) -> None:
        if (
            self.date_fin_mandat
            and self.date_debut_mandat
            and self.date_fin_mandat <= self.date_debut_mandat
        ):
            message = _(
                "La date de fin de mandat doit être postérieure "
                "à la prise de fonction.",
            )
            raise ValidationError({"date_fin_mandat": message})
