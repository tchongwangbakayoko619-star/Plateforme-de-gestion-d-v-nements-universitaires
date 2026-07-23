# gather/users/mixins.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Restreint l'accès à une vue à un ou plusieurs rôles précis.
    Usage : allowed_roles = [User.Role.ORGANISATEUR]
    """

    allowed_roles: list[str] = []

    def test_func(self) -> bool:
        return (
            self.request.user.is_superuser
            or self.request.user.role in self.allowed_roles
        )

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            message = "Vous n'avez pas accès à cette page."
            raise PermissionDenied(message)
        return super().handle_no_permission()
