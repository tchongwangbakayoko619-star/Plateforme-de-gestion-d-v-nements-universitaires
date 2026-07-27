from django.urls import path

from . import views

app_name = "inscriptions"

urlpatterns = [
    path("mes-inscriptions/", views.mes_inscriptions, name="mes_inscriptions"),
    path("<uuid:event_id>/inscrire/", views.s_inscrire, name="inscrire"),
    path(
        "<uuid:inscription_id>/annuler/",
        views.annuler_inscription,
        name="annuler",
    ),
    path(
        "evenement/<uuid:event_id>/",
        views.inscrits_evenement,
        name="inscrits_evenement",
    ),
    path("check-in/", views.check_in, name="check_in"),
    path("checkin/", views.checkin_page_view, name="checkin_page"),
    path(
        "<uuid:inscription_id>/billet/",
        views.billet_view,
        name="billet",
    ),
]
