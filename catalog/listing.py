"""Query-param filtering and facets for the product queryset."""
from decimal import Decimal, InvalidOperation

from django.db.models import Max, Min, QuerySet
from rest_framework.exceptions import ValidationError

from catalog.models import Product

ALLOWED_ORDERING = {"price", "-price"}


def _parse_price(value, field):
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError({field: "Must be a valid number."}) from exc


def parse_list_query(query_params):
    title = query_params.get("title")
    if title is not None:
        title = title.strip() or None

    min_price = _parse_price(query_params.get("min_price"), "min_price")
    max_price = _parse_price(query_params.get("max_price"), "max_price")
    if min_price is not None and max_price is not None and min_price > max_price:
        raise ValidationError({"min_price": "Must be less than or equal to max_price."})

    ordering = query_params.get("ordering")
    if ordering is not None:
        ordering = ordering.strip() or None
        if ordering and ordering not in ALLOWED_ORDERING:
            raise ValidationError({"ordering": "Supported values are 'price' and '-price'."})

    return {
        "title": title,
        "min_price": min_price,
        "max_price": max_price,
        "ordering": ordering,
    }


def build_facets(queryset: QuerySet[Product], title=None):
    """Titles for the location; price bounds for location (and title if selected). Ignore price range."""
    titles = list(
        queryset.order_by().values_list("title", flat=True).distinct().order_by("title")
    )
    priced = queryset.filter(title=title) if title else queryset
    agg = priced.aggregate(min_price=Min("price"), max_price=Max("price"))
    return {
        "titles": titles,
        "min_price": str(agg["min_price"]) if agg["min_price"] is not None else None,
        "max_price": str(agg["max_price"]) if agg["max_price"] is not None else None,
    }


def filter_products(queryset: QuerySet[Product], *, title, min_price, max_price, ordering):
    results = queryset
    if title:
        results = results.filter(title=title)
    if min_price is not None:
        results = results.filter(price__gte=min_price)
    if max_price is not None:
        results = results.filter(price__lte=max_price)
    if ordering == "price":
        return results.order_by("price", "id")
    if ordering == "-price":
        return results.order_by("-price", "-id")
    return results.order_by("id")
