# gather/users/middleware.py
from __future__ import annotations

import zoneinfo

from django.utils import timezone


class TimezoneMiddleware:
    """
    Active le fuseau horaire personnel de l'utilisateur connecté pour
    toute la durée de la requête. Sans ça, User.fuseau_horaire est stocké
    mais n'a aucun effet sur l'affichage des dates/heures.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tzname = getattr(request.user, "fuseau_horaire", None)
        if request.user.is_authenticated and tzname:
            try:
                timezone.activate(zoneinfo.ZoneInfo(tzname))
            except zoneinfo.ZoneInfoNotFoundError:
                timezone.deactivate()
        else:
            timezone.deactivate()

        return self.get_response(request)
