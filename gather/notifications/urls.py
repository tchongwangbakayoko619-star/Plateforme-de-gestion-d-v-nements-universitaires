# gather/notifications/urls.py
from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.liste_notifications, name="liste"),
    path(
        "<uuid:notification_id>/lue/",
        views.marquer_comme_lue,
        name="marquer_lue",
    ),
    path(
        "toutes-lues/",
        views.marquer_toutes_comme_lues,
        name="marquer_toutes_lues",
    ),
    path(
        "<uuid:notification_id>/supprimer/",
        views.supprimer_notification,
        name="supprimer",
    ),
]
