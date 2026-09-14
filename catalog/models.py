from django.db import models


class Product(models.Model):
    JORDAN = "JO"
    SAUDI_ARABIA = "SA"
    LOCATION_CHOICES = [
        (JORDAN, "Jordan"),
        (SAUDI_ARABIA, "Saudi Arabia"),
    ]

    # id from the source CSV, kept distinct from the Django PK so re-imports stay idempotent
    external_id = models.PositiveIntegerField(unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    location = models.CharField(max_length=2, choices=LOCATION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.location})"
