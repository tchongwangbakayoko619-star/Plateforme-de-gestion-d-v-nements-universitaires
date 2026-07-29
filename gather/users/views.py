# gather/users/views.py
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.views.generic import FormView
from django.views.generic import ListView
from django.views.generic import RedirectView
from django.views.generic import TemplateView
from django.views.generic import UpdateView

# gather/users/views.py — ajoute ces vues
from django.views.generic import View

from gather.organizers.forms import OrganizerProfileForm
from gather.students.forms import StudentProfileForm
from gather.users.mixins import RoleRequiredMixin
from gather.users.models import User
from gather.users.services import AdminUserService
from gather.users.services import UserService
from gather.users.tasks import importer_utilisateurs_depuis_csv

from .forms import AdminCreateUserForm
from .forms import AdminImportUsersCSVForm
from .forms import UserProfileForm


class AdminToggleActiveUserView(RoleRequiredMixin, View):
    allowed_roles = [User.Role.ADMIN]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            messages.error(
                request,
                _("Vous ne pouvez pas désactiver votre propre compte."),
            )
        else:
            user.is_active = not user.is_active
            user.save(update_fields=["is_active"])
            messages.success(
                request,
                _("Compte activé.") if user.is_active else _("Compte désactivé."),
            )
        return redirect("users:admin_list")


admin_toggle_active_view = AdminToggleActiveUserView.as_view()


class AdminDeleteUserView(RoleRequiredMixin, View):
    allowed_roles = [User.Role.ADMIN]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        try:
            UserService.supprimer_utilisateur(user, request.user)
            messages.success(request, _("Compte supprimé."))
        except ValidationError as exc:
            message = exc.message if hasattr(exc, "message") else str(exc)
            messages.error(request, message)
        return redirect("users:admin_list")


admin_delete_user_view = AdminDeleteUserView.as_view()


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    # Pas de slug_field/slug_url_kwarg : urls.py utilise <int:pk>/ directement,
    # DetailView sait déjà résoudre "pk" sans configuration supplémentaire.


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["first_name", "last_name"]
    success_message = _("Information successfully updated")

    def get_success_url(self):
        assert self.request.user.is_authenticated
        return self.request.user.get_absolute_url()

    def get_object(self):
        return self.request.user


user_update_view = UserUpdateView.as_view()


class ProfileUpdateView(LoginRequiredMixin, TemplateView):
    """
    Gestion du profil personnel : formulaire User (commun à tous) combiné
    au formulaire spécifique au rôle (Student ou Organizer). Un ADMIN n'a
    que le formulaire User, sans profil métier associé.
    """

    template_name = "users/profile.html"

    def get_profile_form_class(self):
        if self.request.user.is_etudiant:
            return StudentProfileForm
        if self.request.user.is_organisateur:
            return OrganizerProfileForm
        return None

    def get_profile_instance(self):
        if self.request.user.is_etudiant:
            return getattr(self.request.user, "student_profile", None)
        if self.request.user.is_organisateur:
            return getattr(self.request.user, "organizer_profile", None)
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_form_class = self.get_profile_form_class()

        context["user_form"] = kwargs.get(
            "user_form",
            UserProfileForm(instance=self.request.user),
        )
        context["profile_form"] = kwargs.get(
            "profile_form",
            profile_form_class(instance=self.get_profile_instance())
            if profile_form_class
            else None,
        )
        return context

    def post(self, request, *args, **kwargs):
        user_form = UserProfileForm(
            request.POST,
            request.FILES,
            instance=request.user,
        )

        profile_form_class = self.get_profile_form_class()
        profile_form = None
        if profile_form_class:
            profile_form = profile_form_class(
                request.POST,
                request.FILES,
                instance=self.get_profile_instance(),
            )

        forms_valid = user_form.is_valid() and (
            profile_form is None or profile_form.is_valid()
        )
        if not forms_valid:
            context = self.get_context_data(
                user_form=user_form,
                profile_form=profile_form,
            )
            return self.render_to_response(context)

        with transaction.atomic():
            user_form.save()
            if profile_form:
                profile_form.save()

        messages.success(request, _("Profil mis à jour avec succès."))
        return redirect(reverse("users:profile"))


profile_update_view = ProfileUpdateView.as_view()


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


class AdminUserListView(RoleRequiredMixin, ListView):
    """Liste des utilisateurs, réservée aux administrateurs."""

    model = User
    template_name = "users/admin_list.html"
    context_object_name = "users"
    allowed_roles = [User.Role.ADMIN]
    paginate_by = 25

    def get_queryset(self):
        filters = {}
        role = self.request.GET.get("role")
        search = self.request.GET.get("search")
        if role:
            filters["role"] = role
        if search:
            filters["search"] = search
        return UserService.get_users(filters=filters or None)


admin_user_list_view = AdminUserListView.as_view()


class AdminImportUsersView(RoleRequiredMixin, FormView):
    """
    Import en masse d'utilisateurs depuis un fichier CSV, traité en
    arrière-plan via Celery pour ne pas bloquer la requête HTTP de l'admin.
    Un rapport détaillé est envoyé par email une fois l'import terminé.
    """

    template_name = "users/admin_import_users.html"
    form_class = AdminImportUsersCSVForm
    allowed_roles = [User.Role.ADMIN]
    success_url = reverse_lazy("users:admin_list")

    def form_valid(self, form):
        fichier = form.cleaned_data["fichier_csv"]
        csv_content = fichier.read().decode("utf-8")

        importer_utilisateurs_depuis_csv.delay(csv_content, self.request.user.id)

        messages.success(
            self.request,
            _(
                "Import lancé en arrière-plan. Vous recevrez un rapport "
                "par email une fois terminé.",
            ),
        )
        return redirect(self.success_url)


admin_import_users_view = AdminImportUsersView.as_view()
