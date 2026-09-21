from django.db import transaction
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

from orders.mail import attach_receipt_email_on_close, should_send_receipt_email
from orders.models import Order
from orders.serializers import OrderCreateSerializer, OrderReceiptSerializer
from orders.vouchers import create_purchased_order

_RECEIPT_EXAMPLE = {
    "id": 1,
    "product_title": "Sword of Valor",
    "unit_price": "150.00",
    "location": "JO",
    "created_at": "2026-09-13T10:00:00Z",
    "user": "demo",
}


@extend_schema_view(
    retrieve=extend_schema(
        summary="Re-fetch a receipt",
        description="Returns a previously created order. Only the owning user's order is visible; others 404.",
        parameters=[OpenApiParameter("id", int, OpenApiParameter.PATH)],
        responses=OrderReceiptSerializer,
        examples=[OpenApiExample("Receipt", value=_RECEIPT_EXAMPLE, response_only=True)],
    ),
)
class OrderViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Purchase flow: buy a single product and re-fetch its receipt."""

    def get_queryset(self):
        # scoped to the caller so retrieve() 404s on another user's order instead of leaking it
        return Order.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        return OrderCreateSerializer if self.action == "create" else OrderReceiptSerializer

    @extend_schema(
        summary="Buy a product",
        description=(
            "Creates an order for exactly one product (quantity is always 1) and returns a receipt. "
            "A voucher is stored on the order; a receipt email is sent after this response is delivered."
        ),
        request=OrderCreateSerializer,
        responses={201: OrderReceiptSerializer},
        examples=[
            OpenApiExample("Buy product 1", value={"product": 1}, request_only=True),
            OpenApiExample("Receipt", value=_RECEIPT_EXAMPLE, response_only=True),
        ],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data["product"]

        with transaction.atomic():
            order = create_purchased_order(user=request.user, product=product)

        receipt = OrderReceiptSerializer(order)
        response = Response(receipt.data, status=status.HTTP_201_CREATED)
        # Mail starts from response.close() after the body is sent — not during this request.
        if should_send_receipt_email(request.user):
            attach_receipt_email_on_close(response, order.pk)
        return response
