# gather/users/views.py
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.views.generic import FormView
from django.views.generic import RedirectView
from django.views.generic import UpdateView

from gather.users.mixins import RoleRequiredMixin
from gather.users.models import User
from gather.users.services import AdminUserService

from .forms import AdminCreateUserForm


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    # Pas de slug_field/slug_url_kwarg : urls.py utilise <int:pk>/ directement,
    # DetailView sait déjà résoudre "pk" sans configuration supplémentaire.


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    fields = ["first_name", "last_name"]
    success_message = _("Information successfully updated")

    def get_success_url(self):
        assert self.request.user.is_authenticated
        return self.request.user.get_absolute_url()

    def get_object(self):
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse("users:detail", kwargs={"pk": self.request.user.pk})


user_redirect_view = UserRedirectView.as_view()


class AdminCreateUserView(RoleRequiredMixin, FormView):
    """
    Vue réservée aux administrateurs pour créer un utilisateur
    (avec son profil Student/Organizer associé) depuis le back-office.
    """

    template_name = "users/admin_create_user.html"
    form_class = AdminCreateUserForm
    allowed_roles = [User.Role.ADMIN]
    success_url = reverse_lazy("users:admin_list")

    def form_valid(self, form):
        try:
            user = AdminUserService.creer_utilisateur_avec_profil(
                data=form.cleaned_data,
                admin_user=self.request.user,
            )
        except ValidationError as e:
            form.add_error(None, e.message if hasattr(e, "message") else str(e))
            return self.form_invalid(form)

        messages.success(
            self.request,
            _("Utilisateur %(email)s créé avec succès.") % {"email": user.email},
        )
        return redirect(self.success_url)