from __future__ import annotations

import datetime
import uuid

from django.contrib.auth import get_user_model
from django.utils import timezone

from gather.events.models import Event
from gather.organizers.models import Organizer
from gather.students.models import Student

User = get_user_model()


def creer_user(role: str, **kwargs) -> User:
    email = kwargs.pop("email", f"{uuid.uuid4().hex[:10]}@test.local")
    return User.objects.create_user(
        email=email,
        first_name=kwargs.pop("first_name", "Test"),
        last_name=kwargs.pop("last_name", "User"),
        password="motdepasse123!",  # noqa: S106
        role=role,
        **kwargs,
    )


def creer_organizer(**kwargs) -> Organizer:
    user = creer_user(User.Role.ORGANISATEUR)
    return Organizer.objects.create(
        user=user,
        club=kwargs.pop("club", "Club Test"),
        departement=kwargs.pop("departement", "Informatique"),
        date_debut_mandat=kwargs.pop(
            "date_debut_mandat",
            timezone.now().date() - datetime.timedelta(days=30),
        ),
        date_fin_mandat=kwargs.pop(
            "date_fin_mandat",
            timezone.now().date() + datetime.timedelta(days=335),
        ),
        **kwargs,
    )


def creer_student(**kwargs) -> Student:
    user = creer_user(User.Role.ETUDIANT)
    return Student.objects.create(
        user=user,
        matricule=kwargs.pop("matricule", uuid.uuid4().hex[:12]),
        filiere=kwargs.pop("filiere", "Informatique"),
        departement=kwargs.pop("departement", "Informatique"),
        niveau_etude=kwargs.pop("niveau_etude", "L3"),
        promotion=kwargs.pop("promotion", "2025-2026"),
        **kwargs,
    )


def creer_admin_user(**kwargs) -> User:
    return creer_user(User.Role.ADMIN, **kwargs)


def creer_event(
    organizer: Organizer,
    *,
    statut: str = Event.Statut.DRAFT,
    date_debut: datetime.datetime | None = None,
    date_fin: datetime.datetime | None = None,
    **kwargs,
) -> Event:
    date_debut = date_debut or timezone.now() + datetime.timedelta(days=1)
    date_fin = date_fin or date_debut + datetime.timedelta(hours=3)
    capacite_max = kwargs.pop("capacite_max", 100)
    return Event.objects.create(
        organizer=organizer,
        titre=kwargs.pop("titre", "Événement de test"),
        description=kwargs.pop("description", "Description de test."),
        lieu=kwargs.pop("lieu", "Amphi A"),
        date_debut=date_debut,
        date_fin=date_fin,
        capacite_max=capacite_max,
        places_restantes=kwargs.pop("places_restantes", capacite_max),
        statut=statut,
        **kwargs,
    )
