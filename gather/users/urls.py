from django.urls import path

from .views import AdminCreateUserView
from .views import admin_delete_user_view
from .views import admin_import_users_view
from .views import admin_toggle_active_view
from .views import admin_user_list_view
from .views import profile_update_view
from .views import user_detail_view
from .views import user_redirect_view
from .views import user_update_view

app_name = "users"
urlpatterns = [
    path(
        "admin/<int:pk>/toggle-actif/",
        view=admin_toggle_active_view,
        name="admin_toggle_active",
    ),
    path(
        "admin/<int:pk>/supprimer/",
        view=admin_delete_user_view,
        name="admin_delete",
    ),
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("profile/", view=profile_update_view, name="profile"),
    path("admin/liste/", view=admin_user_list_view, name="admin_list"),
    path("admin/creer/", view=AdminCreateUserView.as_view(), name="admin_create"),
    path("admin/importer/", view=admin_import_users_view, name="admin_import"),
    path("<int:pk>/", view=user_detail_view, name="detail"),
]
