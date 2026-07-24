from __future__ import annotations

import typing

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

if typing.TYPE_CHECKING:
    from allauth.socialaccount.models import SocialLogin
    from django.http import HttpRequest

from gather.users.models import User


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest) -> bool:
        return False


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(
        self,
        request: HttpRequest,
        sociallogin: SocialLogin,
    ) -> bool:
        # Jamais de création via OAuth, uniquement connexion à un compte
        # existant.
        return False

    def populate_user(
        self,
        request: HttpRequest,
        sociallogin: SocialLogin,
        data: dict,
    ) -> User:
        """
        Un compte créé via Google/GitHub obtient toujours le rôle
        ÉTUDIANT par défaut. Un organisateur ou administrateur doit
        être promu explicitement — jamais via l'auto-inscription OAuth.
        """
        user = super().populate_user(request, sociallogin, data)
        user.role = User.Role.ETUDIANT
        return user
