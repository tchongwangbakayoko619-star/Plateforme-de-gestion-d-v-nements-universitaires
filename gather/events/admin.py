# gather/events/admin.py
import logging

from django.contrib import admin
from django.utils.html import format_html

from .models import Event
from .models import EventReview
from .models import EventStatusHistory
from .services import EventPermissionError
from .services import EventService
from .services import InvalidTransitionError

logger = logging.getLogger(__name__)

LONGUEUR_COMMENTAIRE_COURT = 50


class EventStatusHistoryInline(admin.TabularInline):
    model = EventStatusHistory
    extra = 0
    readonly_fields = (
        "ancien_statut",
        "nouveau_statut",
        "utilisateur",
        "commentaire",
        "created_at",
    )
    fields = readonly_fields
    can_delete = False
    max_num = 0


class EventReviewInline(admin.TabularInline):
    model = EventReview
    extra = 0
    readonly_fields = ("student", "note", "commentaire", "created_at", "updated_at")
    fields = readonly_fields
    can_delete = False
    max_num = 0


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        "titre",
        "organisateur",
        "categorie",
        "statut_badge",
        "date_debut",
        "date_fin",
        "places_restantes",
        "capacite_max",
        "moyenne_notes",
    ]
    list_filter = ["statut", "categorie", "type_paiement"]
    search_fields = ["titre", "description", "lieu", "organizer__user__email"]
    readonly_fields = ("id", "created_at", "updated_at", "published_at")
    date_hierarchy = "date_debut"
    ordering = ["-date_debut"]
    inlines = [EventStatusHistoryInline, EventReviewInline]
    actions = [
        "approuver_selectionnes",
        "refuser_selectionnes",
        "archiver_selectionnes",
    ]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "id",
                    "organizer",
                    "titre",
                    "description",
                    "categorie",
                    "image",
                ),
            },
        ),
        ("Lieu", {"fields": ("lieu", "latitude", "longitude")}),
        ("Dates", {"fields": ("date_debut", "date_fin")}),
        ("Capacité", {"fields": ("capacite_max", "places_restantes")}),
        ("Paiement", {"fields": ("type_paiement", "prix", "devise")}),
        ("Statut", {"fields": ("statut", "motif_refus", "published_at")}),
        ("Métadonnées", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Statut", ordering="statut")
    def statut_badge(self, obj):
        colors = {
            Event.Statut.DRAFT: "secondary",
            Event.Statut.PENDING: "warning",
            Event.Statut.REVISION_REQUESTED: "info",
            Event.Statut.PUBLISHED: "success",
            Event.Statut.REJECTED: "danger",
            Event.Statut.CANCELLED: "danger",
            Event.Statut.FINISHED: "primary",
            Event.Statut.ARCHIVED: "dark",
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            colors.get(obj.statut, "secondary"),
            obj.get_statut_display(),
        )

    @admin.display(description="Organisateur")
    def organisateur(self, obj):
        return obj.organizer.user.email

    @admin.display(description="Note moyenne")
    def moyenne_notes(self, obj):
        moyenne = EventReview.moyenne_note(obj)
        if moyenne:
            return format_html("⭐ {}", f"{moyenne:.1f}")
        return "-"

    @admin.action(description="Approuver les événements sélectionnés")
    def approuver_selectionnes(self, request, queryset):
        count = 0
        for event in queryset.filter(statut=Event.Statut.PENDING):
            try:
                EventService.approuver(event, request.user)
                count += 1
            except InvalidTransitionError, EventPermissionError:
                logger.warning(
                    "Impossible d'approuver l'événement %s depuis l'admin.",
                    event.id,
                )
        self.message_user(request, f"{count} événement(s) approuvé(s).")

    @admin.action(description="Refuser les événements sélectionnés")
    def refuser_selectionnes(self, request, queryset):
        count = 0
        motif_par_defaut = "Refusé depuis l'admin."
        for event in queryset.filter(statut=Event.Statut.PENDING):
            try:
                EventService.refuser(event, request.user, motif=motif_par_defaut)
                count += 1
            except InvalidTransitionError, EventPermissionError:
                logger.warning(
                    "Impossible de refuser l'événement %s depuis l'admin.",
                    event.id,
                )
        self.message_user(request, f"{count} événement(s) refusé(s).")

    @admin.action(description="Archiver les événements sélectionnés")
    def archiver_selectionnes(self, request, queryset):
        count = 0
        statuts_archivables = (
            Event.Statut.REJECTED,
            Event.Statut.CANCELLED,
            Event.Statut.FINISHED,
        )
        for event in queryset.filter(statut__in=statuts_archivables):
            try:
                EventService.archiver(event, request.user)
                count += 1
            except InvalidTransitionError, EventPermissionError:
                logger.warning(
                    "Impossible d'archiver l'événement %s depuis l'admin.",
                    event.id,
                )
        self.message_user(request, f"{count} événement(s) archivé(s).")


@admin.register(EventReview)
class EventReviewAdmin(admin.ModelAdmin):
    list_display = ["event", "student", "note", "commentaire_court", "created_at"]
    list_filter = ["note", "created_at"]
    search_fields = ["event__titre", "student__user__email", "commentaire"]
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Commentaire")
    def commentaire_court(self, obj):
        if len(obj.commentaire) > LONGUEUR_COMMENTAIRE_COURT:
            return obj.commentaire[:LONGUEUR_COMMENTAIRE_COURT] + "..."
        return obj.commentaire


@admin.register(EventStatusHistory)
class EventStatusHistoryAdmin(admin.ModelAdmin):
    list_display = [
        "event",
        "ancien_statut",
        "nouveau_statut",
        "utilisateur",
        "created_at",
    ]
    list_filter = ["ancien_statut", "nouveau_statut", "created_at"]
    search_fields = ["event__titre", "utilisateur__email"]
    readonly_fields = (
        "event",
        "ancien_statut",
        "nouveau_statut",
        "utilisateur",
        "commentaire",
        "created_at",
    )
