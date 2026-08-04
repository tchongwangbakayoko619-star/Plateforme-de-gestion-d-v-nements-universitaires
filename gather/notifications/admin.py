# gather/notifications/admin.py
from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["destinataire", "type", "titre", "lu", "created_at"]
    list_filter = ["type", "lu"]
    search_fields = ["destinataire__email", "titre", "message"]
    readonly_fields = ("id", "created_at")
