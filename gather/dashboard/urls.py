# gather/dashboard/urls.py
from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard_redirect_view, name="redirect"),
    path("admin/", views.admin_dashboard_view, name="admin"),
    path("organisateur/", views.organizer_dashboard_view, name="organizer"),
    path("etudiant/", views.student_dashboard_view, name="student"),
]
