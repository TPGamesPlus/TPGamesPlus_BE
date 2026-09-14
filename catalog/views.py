from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from catalog import store
from catalog.serializers import ProductDetailSerializer, ProductListSerializer
from core.pagination import StandardResultsSetPagination


class ProductViewSet(viewsets.ViewSet):
    """Read-only product catalog served from the in-process map in catalog/store.py (no per-request DB hit)."""

    pagination_class = StandardResultsSetPagination

    @extend_schema(
        summary="List products",
        description="Paginated product list, optionally filtered by location.",
        parameters=[
            OpenApiParameter("location", str, description="Filter by location: JO or SA", required=False),
            OpenApiParameter("page", int, description="Page number (default 1)", required=False),
            OpenApiParameter("page_size", int, description="Items per page (default 10, max 50)", required=False),
        ],
        # no response example here: drf-spectacular double-nests list examples under auto pagination envelopes;
        # "Try it out" against the live server (see README) already shows the real paginated shape.
        responses=ProductListSerializer(many=True),
    )
    def list(self, request):
        location = request.query_params.get("location")
        products = store.list_products(location=location)  # already id-ordered, see store.load_products
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(products, request, view=self)
        serializer = ProductListSerializer(instance=page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        summary="Retrieve product detail",
        parameters=[OpenApiParameter("id", int, OpenApiParameter.PATH)],
        responses=ProductDetailSerializer,
        examples=[
            OpenApiExample(
                "Product detail",
                value={
                    "id": 1,
                    "external_id": 1,
                    "title": "Sword of Valor",
                    "description": "A legendary sword with magical powers",
                    "price": "150.00",
                    "location": "JO",
                },
                response_only=True,
            ),
        ],
    )
    def retrieve(self, request, pk=None):
        try:
            product_id = int(pk)
        except (TypeError, ValueError):
            raise NotFound("Product not found.")

        product = store.get_product(product_id)
        if product is None:
            raise NotFound("Product not found.")

        serializer = ProductDetailSerializer(instance=product)
        return Response(serializer.data)
