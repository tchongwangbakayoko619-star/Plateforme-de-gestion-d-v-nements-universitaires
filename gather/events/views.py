# gather/events/views.py
from __future__ import annotations

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import FormView
from django.views.generic import ListView
from django.views.generic import UpdateView

from gather.inscriptions.models import Inscription
from gather.users.mixins import RoleRequiredMixin
from gather.users.models import User

from .forms import EventAnnulerForm
from .forms import EventForm
from .forms import EventRefuserForm
from .forms import EventReviewForm
from .forms import EventRevisionForm
from .models import Event
from .models import EventReview
from .services import EventPermissionError
from .services import EventService
from .services import InvalidTransitionError
from .services import ReviewService

# Section : consultation publique


class EventListView(ListView):
    """Liste publique des événements publiés."""

    model = Event
    template_name = "events/event_list.html"
    context_object_name = "evenements"
    paginate_by = 12

    def get_queryset(self):
        filters = {
            "statut": Event.Statut.PUBLISHED,
            "categorie": self.request.GET.get("categorie") or None,
            "search": self.request.GET.get("search") or None,
        }
        return EventService.get_evenements(filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categorie_active"] = self.request.GET.get("categorie", "")
        context["search_query"] = self.request.GET.get("search", "")
        context["categories"] = Event.Categorie.choices
        return context


event_list_view = EventListView.as_view()


class EventDetailView(DetailView):
    """Détail public d'un événement, avec ses avis et statistiques."""

    model = Event
    template_name = "events/event_detail.html"
    context_object_name = "event"
    pk_url_kwarg = "event_id"

    def get_queryset(self):
        return Event.objects.select_related("organizer__user")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["avis"] = ReviewService.get_avis_evenement(self.object)
        context["stats"] = ReviewService.get_stats_evenement(self.object)

        user = self.request.user
        context["mon_inscription"] = None
        context["mon_avis"] = None
        if user.is_authenticated:
            student = getattr(user, "student_profile", None)
            if student:
                context["mon_inscription"] = (
                    Inscription.objects.filter(
                        event=self.object,
                        student=student,
                        statut__in=[
                            Inscription.Statut.CONFIRMEE,
                            Inscription.Statut.EN_ATTENTE_PAIEMENT,
                        ],
                    )
                    .select_related("ticket")
                    .first()
                )
                context["mon_avis"] = EventReview.objects.filter(
                    event=self.object,
                    student=student,
                ).first()
        return context


event_detail_view = EventDetailView.as_view()


# Section : gestion organisateur


class OrganizerEventListView(RoleRequiredMixin, ListView):
    """Liste des événements de l'organisateur connecté, tous statuts
    confondus."""

    model = Event
    template_name = "events/organizer_event_list.html"
    context_object_name = "evenements"
    allowed_roles = [User.Role.ORGANISATEUR]
    paginate_by = 20

    def get_queryset(self):
        organizer = self.request.user.organizer_profile
        return EventService.get_evenements({"organisateur_id": organizer.id})


organizer_event_list_view = OrganizerEventListView.as_view()


class EventCreateView(RoleRequiredMixin, FormView):
    """Création d'un événement par un organisateur."""

    template_name = "events/event_form.html"
    form_class = EventForm
    allowed_roles = [User.Role.ORGANISATEUR]

    def form_valid(self, form):
        organizer = self.request.user.organizer_profile
        event = EventService.creer_brouillon(organizer, form.cleaned_data)
        if event.statut == Event.Statut.PENDING:
            messages.success(
                self.request,
                _("Événement créé et envoyé pour validation."),
            )
        else:
            messages.success(self.request, _("Brouillon d'événement créé."))
        self.object = event
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("events:organizer_detail", kwargs={"event_id": self.object.id})


event_create_view = EventCreateView.as_view()


class EventUpdateView(RoleRequiredMixin, FormView):
    """Modification d'un événement en brouillon ou en révision.
    Utilise FormView au lieu de UpdateView pour éviter le conflit
    entre form.save() et EventService.modifier()."""

    form_class = EventForm
    template_name = "events/event_form.html"
    allowed_roles = [User.Role.ORGANISATEUR]

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(
            Event.objects.filter(organizer=request.user.organizer_profile),
            pk=kwargs["event_id"],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        """Pré-remplit le formulaire avec les données de l'événement."""
        return {
            "titre": self.object.titre,
            "description": self.object.description,
            "categorie": self.object.categorie,
            "lieu": self.object.lieu,
            "latitude": self.object.latitude,
            "longitude": self.object.longitude,
            "date_debut": self.object.date_debut.strftime("%Y-%m-%dT%H:%M")
            if self.object.date_debut
            else "",
            "date_fin": self.object.date_fin.strftime("%Y-%m-%dT%H:%M")
            if self.object.date_fin
            else "",
            "capacite_max": self.object.capacite_max,
            "type_paiement": self.object.type_paiement,
            "prix": self.object.prix,
            "devise": self.object.devise,
            "statut": self.object.statut,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.object
        return context

    def form_valid(self, form):
        try:
            EventService.modifier(
                self.object,
                form.cleaned_data,
                self.request.user.organizer_profile,
            )
        except (EventPermissionError, ValidationError) as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        messages.success(self.request, _("Événement mis à jour."))
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("events:organizer_detail", kwargs={"event_id": self.object.id})


event_update_view = EventUpdateView.as_view()


class EventDeleteView(RoleRequiredMixin, DeleteView):
    """Suppression d'un événement (brouillon, refusé ou en révision
    uniquement — vérifié par EventService)."""

    model = Event
    template_name = "events/event_confirm_delete.html"
    pk_url_kwarg = "event_id"
    allowed_roles = [User.Role.ORGANISATEUR]
    success_url = reverse_lazy("events:organizer_list")

    def get_queryset(self):
        return Event.objects.filter(organizer=self.request.user.organizer_profile)

    def form_valid(self, form):
        try:
            EventService.supprimer(self.object, self.request.user.organizer_profile)
        except (EventPermissionError, ValidationError) as exc:
            messages.error(self.request, str(exc))
            return redirect(
                reverse("events:organizer_detail", kwargs={"event_id": self.object.id}),
            )
        messages.success(self.request, _("Événement supprimé."))
        return redirect(self.success_url)


event_delete_view = EventDeleteView.as_view()


# Section : workflow, actions organisateur


class EventSoumettreView(RoleRequiredMixin, View):
    """Soumission d'un brouillon pour validation administrative."""

    allowed_roles = [User.Role.ORGANISATEUR]

    def post(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        try:
            EventService.soumettre(event, request.user.organizer_profile)
        except (EventPermissionError, InvalidTransitionError) as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, _("Événement soumis pour validation."))
        return redirect(
            reverse("events:organizer_detail", kwargs={"event_id": event_id}),
        )


event_soumettre_view = EventSoumettreView.as_view()


# Section : workflow, actions administrateur


class AdminEventListView(RoleRequiredMixin, ListView):
    model = Event
    template_name = "events/admin_event_list.html"
    context_object_name = "evenements"
    allowed_roles = [User.Role.ADMIN]
    paginate_by = 25

    def get_queryset(self):
        statut = self.request.GET.get("statut", Event.Statut.PENDING)
        return EventService.get_evenements({"statut": statut})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuts_disponibles"] = Event.Statut.choices
        return context


admin_event_list_view = AdminEventListView.as_view()


class EventApprouverView(RoleRequiredMixin, View):
    allowed_roles = [User.Role.ADMIN]

    def post(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        try:
            EventService.approuver(event, request.user)
        except InvalidTransitionError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, _("Événement approuvé et publié."))
        return redirect(reverse("events:admin_list"))


event_approuver_view = EventApprouverView.as_view()


class EventRefuserView(RoleRequiredMixin, FormView):
    allowed_roles = [User.Role.ADMIN]
    form_class = EventRefuserForm
    template_name = "events/event_refuser_form.html"

    def get_event(self):
        return get_object_or_404(Event, pk=self.kwargs["event_id"])

    def form_valid(self, form):
        event = self.get_event()
        try:
            EventService.refuser(
                event,
                self.request.user,
                motif=form.cleaned_data["motif"],
            )
        except InvalidTransitionError as exc:
            messages.error(self.request, str(exc))
        else:
            messages.success(self.request, _("Événement refusé."))
        return redirect(reverse("events:admin_list"))


event_refuser_view = EventRefuserView.as_view()


class EventDemanderRevisionView(RoleRequiredMixin, FormView):
    allowed_roles = [User.Role.ADMIN]
    form_class = EventRevisionForm
    template_name = "events/event_revision_form.html"

    def get_event(self):
        return get_object_or_404(Event, pk=self.kwargs["event_id"])

    def form_valid(self, form):
        event = self.get_event()
        try:
            EventService.demander_revision(
                event,
                self.request.user,
                commentaire=form.cleaned_data["commentaire"],
            )
        except InvalidTransitionError as exc:
            messages.error(self.request, str(exc))
        else:
            messages.success(self.request, _("Révision demandée à l'organisateur."))
        return redirect(reverse("events:admin_list"))


event_demander_revision_view = EventDemanderRevisionView.as_view()


class EventAnnulerView(RoleRequiredMixin, FormView):
    allowed_roles = [User.Role.ADMIN]
    form_class = EventAnnulerForm
    template_name = "events/event_annuler_form.html"

    def get_event(self):
        return get_object_or_404(Event, pk=self.kwargs["event_id"])

    def form_valid(self, form):
        event = self.get_event()
        try:
            EventService.annuler(
                event,
                self.request.user,
                commentaire=form.cleaned_data["commentaire"],
            )
        except InvalidTransitionError as exc:
            messages.error(self.request, str(exc))
        else:
            messages.success(self.request, _("Événement annulé."))
        return redirect(reverse("events:admin_list"))


event_annuler_view = EventAnnulerView.as_view()


class EventArchiverView(RoleRequiredMixin, View):
    allowed_roles = [User.Role.ADMIN]

    def post(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        try:
            EventService.archiver(event, request.user)
        except InvalidTransitionError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, _("Événement archivé."))
        return redirect(reverse("events:admin_list"))


event_archiver_view = EventArchiverView.as_view()


# Section : avis soumis par les étudiants


class EventReviewCreateView(RoleRequiredMixin, FormView):
    """Un étudiant ajoute son avis sur un événement terminé."""

    form_class = EventReviewForm
    template_name = "events/review_form.html"
    allowed_roles = [User.Role.ETUDIANT]

    def get_event(self):
        return get_object_or_404(Event, pk=self.kwargs["event_id"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["event"] = self.get_event()
        return context

    def form_valid(self, form):
        event = self.get_event()
        student = self.request.user.student_profile

        if not Inscription.objects.filter(
            event=event,
            student=student,
            statut=Inscription.Statut.CONFIRMEE,
        ).exists():
            form.add_error(
                None,
                _(
                    "Vous devez être inscrit et avoir payé cet "
                    "événement pour laisser un avis.",
                ),
            )
            return self.form_invalid(form)

        try:
            ReviewService.ajouter_avis(
                student,
                event,
                note=form.cleaned_data["note"],
                commentaire=form.cleaned_data["commentaire"],
            )
        except ValidationError as exc:
            message = exc.message if hasattr(exc, "message") else str(exc)
            form.add_error(None, message)
            return self.form_invalid(form)

        messages.success(self.request, _("Votre avis a été enregistré."))
        return redirect(reverse("events:detail", kwargs={"event_id": event.id}))


event_review_create_view = EventReviewCreateView.as_view()


class EventReviewUpdateView(RoleRequiredMixin, UpdateView):
    model = EventReview
    form_class = EventReviewForm
    template_name = "events/review_form.html"
    pk_url_kwarg = "review_id"
    allowed_roles = [User.Role.ETUDIANT]

    def get_queryset(self):
        return EventReview.objects.filter(student=self.request.user.student_profile)

    def form_valid(self, form):
        try:
            ReviewService.modifier_avis(
                self.object,
                self.request.user.student_profile,
                note=form.cleaned_data["note"],
                commentaire=form.cleaned_data["commentaire"],
            )
        except (EventPermissionError, ValidationError) as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        messages.success(self.request, _("Votre avis a été modifié."))
        return redirect(
            reverse("events:detail", kwargs={"event_id": self.object.event_id}),
        )


event_review_update_view = EventReviewUpdateView.as_view()


class EventReviewDeleteView(RoleRequiredMixin, DeleteView):
    model = EventReview
    template_name = "events/review_confirm_delete.html"
    pk_url_kwarg = "review_id"
    allowed_roles = [User.Role.ETUDIANT]

    def get_queryset(self):
        return EventReview.objects.filter(student=self.request.user.student_profile)

    def form_valid(self, form):
        event_id = self.object.event_id
        try:
            ReviewService.supprimer_avis(self.object, self.request.user.student_profile)
        except EventPermissionError as exc:
            messages.error(self.request, str(exc))
        else:
            messages.success(self.request, _("Votre avis a été supprimé."))
        return redirect(reverse("events:detail", kwargs={"event_id": event_id}))


event_review_delete_view = EventReviewDeleteView.as_view()
