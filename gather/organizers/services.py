# gather/organizers/services.py
import logging

from django.core.exceptions import ValidationError

from .models import Organizer

logger = logging.getLogger(__name__)


class OrganizerService:
    """Logique métier liée au profil associatif (Organizer)."""

    @staticmethod
    def creer_profil(user, **data) -> Organizer:
        """
        Crée le profil organisateur associé à un user.

        Raises:
            ValidationError: si le user n'a pas le rôle ORGANISATEUR,
                              ou si un profil existe déjà.
        """
        if not user.is_organisateur:
            message = (
                "Seul un utilisateur avec le rôle ORGANISATEUR peut avoir "
                "un profil Organizer."
            )
            raise ValidationError(message)

        if hasattr(user, "organizer_profile"):
            message = f"{user.email} a déjà un profil organisateur."
            raise ValidationError(message)

        club = data.get("club", "").strip()
        if not club:
            message = "Le club / association est requis."
            raise ValidationError(message)

        organizer = Organizer(
            user=user,
            club=club,
            departement=data.get("departement", "").strip(),
            poste=data.get("poste", Organizer.Poste.MEMBRE),
            date_debut_mandat=data.get("date_debut_mandat"),
            date_fin_mandat=data.get("date_fin_mandat"),
            bureau_local=data.get("bureau_local", "").strip(),
            biographie=data.get("biographie", "").strip(),
        )
        organizer.full_clean()  # déclenche clean() : cohérence des dates de mandat
        organizer.save()

        logger.info("Profil organisateur créé pour %s (club: %s)", user.email, club)
        return organizer

    @staticmethod
    def modifier_profil(organizer: Organizer, **data) -> Organizer:
        champs_modifiables = [
            "club",
            "departement",
            "poste",
            "date_debut_mandat",
            "date_fin_mandat",
            "bureau_local",
            "biographie",
            "statut",
        ]
        for champ in champs_modifiables:
            if champ in data:
                setattr(organizer, champ, data[champ])

        organizer.full_clean()
        organizer.save()
        return organizer

    @staticmethod
    def get_organisateurs(filters: dict | None = None):
        queryset = Organizer.objects.select_related("user").order_by("club")

        if not filters:
            return queryset

        if filters.get("club"):
            queryset = queryset.filter(club__icontains=filters["club"])
        if filters.get("statut"):
            queryset = queryset.filter(statut=filters["statut"])

        return queryset
