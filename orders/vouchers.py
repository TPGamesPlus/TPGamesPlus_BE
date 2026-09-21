import random
import string
import time

from django.db import IntegrityError, transaction

from orders.models import Order

SPECIAL_CHARS = "!@#$%&"
MAX_CODE_ATTEMPTS = 8


def title_prefix(title):
    return "".join(word[0].upper() for word in title.split() if word)


def time_digits(now_ms=None):
    millis = int(time.time() * 1000) if now_ms is None else now_ms
    return f"{millis % 10000:04d}"


def generate_voucher_redeem_code(title, *, now_ms=None, rng=None):
    """Build PREFIX + dd + special + dd + a-z from the game title and a time-based number."""
    rng = rng or random
    digits = time_digits(now_ms)
    special = rng.choice(SPECIAL_CHARS)
    letter = rng.choice(string.ascii_lowercase)
    return f"{title_prefix(title)}{digits[:2]}{special}{digits[2:]}{letter}"


def create_purchased_order(*, user, product):
    last_error = None
    for _ in range(MAX_CODE_ATTEMPTS):
        code = generate_voucher_redeem_code(product.title)
        try:
            with transaction.atomic():
                return Order.objects.create(
                    user=user,
                    product=product,
                    product_title=product.title,
                    unit_price=product.price,
                    location=product.location,
                    voucher_redeem_code=code,
                    voucher_status=Order.VoucherStatus.NEW,
                )
        except IntegrityError as exc:
            last_error = exc
    raise last_error
