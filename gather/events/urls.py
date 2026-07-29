from django.urls import path
from django.views.generic.base import RedirectView

from . import views

app_name = "events"

urlpatterns = [
    # Consultation publique
    path("", views.event_list_view, name="list"),
    path("<uuid:event_id>/", views.event_detail_view, name="detail"),
    # Gestion organisateur
    path("organisateur/", views.organizer_event_list_view, name="organizer_list"),
    path("organisateur/creer/", views.event_create_view, name="organizer_create"),
    path(
        "organisateur/<uuid:event_id>/",
        views.event_detail_view,
        name="organizer_detail",
    ),
    path(
        "organisateur/<uuid:event_id>/modifier/",
        views.event_update_view,
        name="organizer_update",
    ),
    path(
        "organisateur/<uuid:event_id>/supprimer/",
        views.event_delete_view,
        name="organizer_delete",
    ),
    path(
        "organisateur/<uuid:event_id>/soumettre/",
        views.event_soumettre_view,
        name="soumettre",
    ),
    path(
        "organizer/<uuid:event_id>/",
        RedirectView.as_view(pattern_name="events:organizer_detail", permanent=True),
    ),
    # Gestion administrateur
    path("admin/", views.admin_event_list_view, name="admin_list"),
    path(
        "admin/<uuid:event_id>/approuver/",
        views.event_approuver_view,
        name="approuver",
    ),
    path(
        "admin/<uuid:event_id>/refuser/",
        views.event_refuser_view,
        name="refuser",
    ),
    path(
        "admin/<uuid:event_id>/revision/",
        views.event_demander_revision_view,
        name="demander_revision",
    ),
    path(
        "admin/<uuid:event_id>/annuler/",
        views.event_annuler_view,
        name="annuler",
    ),
    path(
        "admin/<uuid:event_id>/archiver/",
        views.event_archiver_view,
        name="archiver",
    ),
    # Avis
    path(
        "<uuid:event_id>/avis/creer/",
        views.event_review_create_view,
        name="review_create",
    ),
    path(
        "avis/<int:review_id>/modifier/",
        views.event_review_update_view,
        name="review_update",
    ),
    path(
        "avis/<int:review_id>/supprimer/",
        views.event_review_delete_view,
        name="review_delete",
    ),
]
