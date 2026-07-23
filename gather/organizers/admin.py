from django.contrib import admin

from .models import Organizer


@admin.register(Organizer)
class OrganizerAdmin(admin.ModelAdmin):
    list_display = ("club", "poste", "user", "statut", "date_debut_mandat")
    list_filter = ("statut", "poste", "club")
    search_fields = ("club", "user__email", "user__first_name", "user__last_name")
    autocomplete_fields = ("user",)
