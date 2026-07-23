from django.contrib import admin

from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("matricule", "user", "filiere", "departement", "statut_academique")
    list_filter = ("departement", "statut_academique", "promotion")
    search_fields = ("matricule", "user__email", "user__first_name", "user__last_name")
    autocomplete_fields = ("user",)
