from rest_framework import serializers

from catalog.models import Product
from orders.models import Order


class OrderCreateSerializer(serializers.Serializer):
    # PrimaryKeyRelatedField validates existence and yields a clear 400 if the product id is unknown
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())


class OrderReceiptSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = Order
        fields = ["id", "product_title", "unit_price", "location", "created_at", "user"]
