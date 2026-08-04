# gather/payments/admin.py
from django.contrib import admin

from .models import Payment
from .models import PaymentTransaction


class PaymentTransactionInline(admin.TabularInline):
    model = PaymentTransaction
    extra = 0
    readonly_fields = ("evenement", "payload_brut", "created_at")
    can_delete = False
    max_num = 0


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "reference_externe",
        "inscription",
        "provider",
        "montant",
        "devise",
        "statut",
        "created_at",
    ]
    list_filter = ["provider", "statut"]
    search_fields = ["reference_externe", "inscription__student__user__email"]
    readonly_fields = ("id", "reference_externe", "created_at", "updated_at")
    inlines = [PaymentTransactionInline]
