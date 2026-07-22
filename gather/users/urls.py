from django.urls import path

from .views import admin_import_users_view
from .views import admin_user_list_view
from .views import user_detail_view
from .views import user_redirect_view
from .views import user_update_view
from .views import AdminCreateUserView

app_name = "users"
urlpatterns = [
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("admin/liste/", view=admin_user_list_view, name="admin_list"),
    path("admin/creer/", view=AdminCreateUserView.as_view(), name="admin_create"),
    path("admin/importer/", view=admin_import_users_view, name="admin_import"),
    path("<int:pk>/", view=user_detail_view, name="detail"),
]