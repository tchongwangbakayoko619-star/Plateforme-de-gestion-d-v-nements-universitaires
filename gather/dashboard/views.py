# gather/dashboard/views.py
from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg
from django.db.models import Count
from django.db.models import Sum
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView

from gather.events.models import Event
from gather.events.models import EventReview
from gather.inscriptions.models import Inscription
from gather.notifications.services import NotificationService
from gather.payments.models import Payment
from gather.users.mixins import RoleRequiredMixin
from gather.users.models import User


class DashboardRedirectView(LoginRequiredMixin, TemplateView):
    """Point d'entrée unique : redirige vers le bon tableau de bord
    selon le rôle de l'utilisateur connecté."""

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.is_administrateur:
            return redirect(reverse("dashboard:admin"))
        if user.is_organisateur:
            return redirect(reverse("dashboard:organizer"))
        return redirect(reverse("dashboard:student"))


dashboard_redirect_view = DashboardRedirectView.as_view()


class AdminDashboardView(RoleRequiredMixin, TemplateView):
    template_name = "dashboard/admin_dashboard.html"
    allowed_roles = [User.Role.ADMIN]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        evenements_par_statut = (
            Event.objects.values("statut")
            .annotate(total=Count("id"))
            .order_by("statut")
        )
        paiements_reussis = Payment.objects.filter(statut=Payment.Statut.REUSSI)

        context.update(
            {
                "en_attente_validation": Event.objects.filter(
                    statut=Event.Statut.PENDING,
                ).count(),
                "evenements_publies": Event.objects.filter(
                    statut=Event.Statut.PUBLISHED,
                ).count(),
                "evenements_par_statut": list(evenements_par_statut),
                "total_inscriptions": Inscription.objects.filter(
                    statut=Inscription.Statut.CONFIRMEE,
                ).count(),
                "total_utilisateurs": User.objects.count(),
                "revenus_total": paiements_reussis.aggregate(total=Sum("montant"))[
                    "total"
                ]
                or 0,
                "evenements_recents": Event.objects.select_related(
                    "organizer__user",
                ).order_by("-created_at")[:10],
                "notifications_non_lues": NotificationService.get_notifications(
                    self.request.user,
                    non_lues_uniquement=True,
                ).count(),
            },
        )
        return context


admin_dashboard_view = AdminDashboardView.as_view()


class OrganizerDashboardView(RoleRequiredMixin, TemplateView):
    template_name = "dashboard/organizer_dashboard.html"
    allowed_roles = [User.Role.ORGANISATEUR]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organizer = self.request.user.organizer_profile
        mes_evenements = Event.objects.filter(organizer=organizer)

        context.update(
            {
                "mes_evenements": mes_evenements.order_by("-created_at")[:10],
                "total_evenements": mes_evenements.count(),
                "en_attente": mes_evenements.filter(
                    statut=Event.Statut.PENDING,
                ).count(),
                "publies": mes_evenements.filter(statut=Event.Statut.PUBLISHED).count(),
                "revision_demandee": mes_evenements.filter(
                    statut=Event.Statut.REVISION_REQUESTED,
                ).count(),
                "total_inscrits": Inscription.objects.filter(
                    event__organizer=organizer,
                    statut=Inscription.Statut.CONFIRMEE,
                ).count(),
                "note_moyenne_globale": EventReview.objects.filter(
                    event__organizer=organizer,
                ).aggregate(moyenne=Avg("note"))["moyenne"],
                "notifications_non_lues": NotificationService.get_notifications(
                    self.request.user,
                    non_lues_uniquement=True,
                ).count(),
            },
        )
        return context


organizer_dashboard_view = OrganizerDashboardView.as_view()


class StudentDashboardView(RoleRequiredMixin, TemplateView):
    template_name = "dashboard/student_dashboard.html"
    allowed_roles = [User.Role.ETUDIANT]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user.student_profile

        mes_inscriptions = (
            Inscription.objects.filter(student=student)
            .select_related("event", "ticket")
            .order_by("-date_inscription")
        )

        context.update(
            {
                "mes_inscriptions": mes_inscriptions[:10],
                "total_inscriptions": mes_inscriptions.filter(
                    statut=Inscription.Statut.CONFIRMEE,
                ).count(),
                "evenements_a_venir": mes_inscriptions.filter(
                    statut=Inscription.Statut.CONFIRMEE,
                    event__statut=Event.Statut.PUBLISHED,
                ).count(),
                "evenements_publies": Event.objects.filter(
                    statut=Event.Statut.PUBLISHED,
                ).order_by("date_debut")[:6],
                "notifications_non_lues": NotificationService.get_notifications(
                    self.request.user,
                    non_lues_uniquement=True,
                ).count(),
            },
        )
        return context


student_dashboard_view = StudentDashboardView.as_view()
