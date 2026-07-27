# gather/statistics/urls.py
from django.urls import path

from . import views

app_name = "statistics"

urlpatterns = [
    path("globales/", views.statistiques_globales, name="globales"),
    path("organisateur/", views.statistiques_organisateur, name="organisateur"),
    path(
        "evenement/<uuid:event_id>/",
        views.statistiques_evenement,
        name="evenement",
    ),
]
