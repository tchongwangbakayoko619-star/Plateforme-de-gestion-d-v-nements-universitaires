# gather/inscriptions/admin.py
from django.contrib import admin

from .models import Inscription
from .models import Ticket


@admin.register(Inscription)
class InscriptionAdmin(admin.ModelAdmin):
    list_display = ["event", "student", "statut", "date_inscription", "date_annulation"]
    list_filter = ["statut"]
    search_fields = ["event__titre", "student__user__email", "student__matricule"]
    readonly_fields = ("id", "date_inscription")
    autocomplete_fields = ("event", "student")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = [
        "code_qr",
        "inscription",
        "statut",
        "created_at",
        "date_utilisation",
    ]
    list_filter = ["statut"]
    search_fields = [
        "code_qr",
        "inscription__event__titre",
        "inscription__student__user__email",
    ]
    readonly_fields = ("id", "code_qr", "image_qr", "created_at", "date_utilisation")
