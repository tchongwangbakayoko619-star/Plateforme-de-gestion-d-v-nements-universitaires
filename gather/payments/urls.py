# gather/payments/urls.py
from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path(
        "<uuid:inscription_id>/initier/",
        views.initier_paiement,
        name="initier",
    ),
    path("webhook/campay/", views.webhook_campay, name="webhook_campay"),
]
