"""Query-param filtering and facets for the in-memory product list."""
from decimal import Decimal, InvalidOperation

from rest_framework.exceptions import ValidationError

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


def build_facets(location_products, title=None):
    """Titles for the location; price bounds for location (and title if selected). Ignore price range."""
    titles = sorted({product["title"] for product in location_products})
    priced = location_products
    if title:
        priced = [product for product in location_products if product["title"] == title]
    prices = [Decimal(product["price"]) for product in priced]
    return {
        "titles": titles,
        "min_price": str(min(prices)) if prices else None,
        "max_price": str(max(prices)) if prices else None,
    }


def filter_products(location_products, *, title, min_price, max_price, ordering):
    results = location_products
    if title:
        results = [product for product in results if product["title"] == title]
    if min_price is not None:
        results = [product for product in results if Decimal(product["price"]) >= min_price]
    if max_price is not None:
        results = [product for product in results if Decimal(product["price"]) <= max_price]
    if ordering:
        reverse = ordering == "-price"
        results = sorted(
            results,
            key=lambda product: (Decimal(product["price"]), product["id"]),
            reverse=reverse,
        )
    return results
