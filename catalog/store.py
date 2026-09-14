"""In-process shared map of products (id -> JSON), no Redis: rebuilt at startup and on every re-import."""
import json
import threading

from catalog.models import Product

_lock = threading.Lock()

PRODUCTS: dict[int, str] = {}
PRODUCT_IDS_BY_LOCATION: dict[str, list[int]] = {}


def _serialize(product: Product) -> dict:
    return {
        "id": product.pk,
        "external_id": product.external_id,
        "title": product.title,
        "description": product.description,
        "price": str(product.price),
        "location": product.location,
    }


def load_products() -> None:
    """Rebuild the in-memory map from the DB; call at startup and after every (re-)import."""
    products: dict[int, str] = {}
    by_location: dict[str, list[int]] = {}

    for product in Product.objects.order_by("id"):
        products[product.pk] = json.dumps(_serialize(product))
        by_location.setdefault(product.location, []).append(product.pk)

    with _lock:
        PRODUCTS.clear()
        PRODUCTS.update(products)
        PRODUCT_IDS_BY_LOCATION.clear()
        PRODUCT_IDS_BY_LOCATION.update(by_location)


def get_product(product_id: int) -> dict | None:
    with _lock:
        raw = PRODUCTS.get(product_id)
    return json.loads(raw) if raw is not None else None


def list_products(location: str | None = None) -> list[dict]:
    with _lock:
        if location:
            ids = PRODUCT_IDS_BY_LOCATION.get(location, [])
            raws = [PRODUCTS[i] for i in ids if i in PRODUCTS]
        else:
            raws = list(PRODUCTS.values())
    return [json.loads(raw) for raw in raws]
