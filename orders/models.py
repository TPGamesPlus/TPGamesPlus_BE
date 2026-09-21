from django.conf import settings
from django.db import models

from catalog.models import Product


class Order(models.Model):
    class VoucherStatus(models.TextChoices):
        NEW = "NEW", "New"
        REDEEMED = "REDEEMED", "Redeemed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="orders")
    # snapshots so a receipt stays correct even if the product changes/is removed later
    product_title = models.CharField(max_length=255)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    location = models.CharField(max_length=2, choices=Product.LOCATION_CHOICES)
    voucher_redeem_code = models.CharField(max_length=128, unique=True, null=True)
    voucher_status = models.CharField(
        max_length=16,
        choices=VoucherStatus.choices,
        default=VoucherStatus.NEW,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} - {self.product_title} ({self.user})"
