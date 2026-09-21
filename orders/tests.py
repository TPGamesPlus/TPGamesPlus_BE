from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework import status

from catalog.models import Product
from orders.item_images import item_image_path
from orders.mail import attach_receipt_email_on_close
from orders.models import Order
from orders.vouchers import SPECIAL_CHARS, generate_voucher_redeem_code


RECEIPT_FIELDS = {"id", "product_title", "unit_price", "location", "created_at", "user"}


@pytest.fixture
def product(db):
    return Product.objects.create(external_id=1, title="Sword", description="d", price="19.99", location="JO")


@pytest.fixture
def mapped_product(db):
    return Product.objects.create(
        external_id=2, title="Sword of Valor", description="d", price="150.00", location="JO"
    )


@pytest.fixture
def inline_email_threads(monkeypatch):
    class ImmediateThread:
        def __init__(self, target=None, args=(), kwargs=None, daemon=None, name=None):
            self._target = target
            self._args = args
            self._kwargs = kwargs or {}

        def start(self):
            self._target(*self._args, **self._kwargs)

    monkeypatch.setattr("orders.mail.threading.Thread", ImmediateThread)


class TestOrders:
    def test_orders_require_auth(self, api_client, product):
        response = api_client.post("/api/orders/", {"product": product.id}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_order_snapshots_price(self, auth_client, product, user):
        response = auth_client.post("/api/orders/", {"product": product.id}, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["product_title"] == "Sword"
        assert response.data["unit_price"] == "19.99"
        order = Order.objects.get(pk=response.data["id"])
        assert order.user == user

    def test_create_order_stores_new_voucher_without_exposing_it(self, auth_client, product):
        response = auth_client.post("/api/orders/", {"product": product.id}, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert set(response.data) == RECEIPT_FIELDS
        order = Order.objects.get(pk=response.data["id"])
        assert order.voucher_status == Order.VoucherStatus.NEW
        assert order.voucher_redeem_code
        assert order.voucher_redeem_code.startswith("S")
        assert order.voucher_redeem_code[-1].islower()
        assert order.voucher_redeem_code[-4] in SPECIAL_CHARS

    def test_buy_nonexistent_product_returns_400(self, auth_client):
        response = auth_client.post("/api/orders/", {"product": 999999}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_retrieve_own_order(self, auth_client, product):
        create_response = auth_client.post("/api/orders/", {"product": product.id}, format="json")
        response = auth_client.get(f"/api/orders/{create_response.data['id']}/")
        assert response.status_code == status.HTTP_200_OK
        assert set(response.data) == RECEIPT_FIELDS

    def test_retrieve_other_users_order_returns_404(self, auth_client, other_auth_client, product):
        create_response = auth_client.post("/api/orders/", {"product": product.id}, format="json")
        response = other_auth_client.get(f"/api/orders/{create_response.data['id']}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestVoucherGenerator:
    def test_prefix_time_digits_special_and_letter(self):
        class FixedRng:
            def choice(self, seq):
                return "!" if seq == SPECIAL_CHARS else "k"

        code = generate_voucher_redeem_code("Sword of Valor", now_ms=1423, rng=FixedRng())
        assert code == "SOV14!23k"

    def test_skips_empty_tokens(self):
        class FixedRng:
            def choice(self, seq):
                return "@" if seq == SPECIAL_CHARS else "z"

        code = generate_voucher_redeem_code("  Shield   of  Aegis ", now_ms=99, rng=FixedRng())
        assert code == "SOA00@99z"


class TestReceiptEmail:
    def test_mail_job_starts_only_on_close(self, inline_email_threads, db):
        from django.http import HttpResponse

        response = HttpResponse()
        with patch("orders.mail.send_order_receipt_email") as send:
            attach_receipt_email_on_close(response, 42)
            send.assert_not_called()
            response.close()
            send.assert_called_once_with(42)

    @override_settings(SENDGRID_API_KEY="sg-test", SENDGRID_FROM_EMAIL="store@example.com")
    @patch("orders.mail.SendGridAPIClient")
    def test_email_sent_after_successful_purchase(
        self, mock_client, inline_email_threads, email_auth_client, mapped_product
    ):
        mock_client.return_value.send.return_value = None
        response = email_auth_client.post("/api/orders/", {"product": mapped_product.id}, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        mock_client.assert_called_once_with("sg-test")
        mail = mock_client.return_value.send.call_args.args[0]
        payload = mail.get()
        html = next(part["value"] for part in payload["content"] if "html" in part["type"])
        order = Order.objects.get(pk=response.data["id"])
        assert "carol@example.com" in str(payload["personalizations"])
        assert order.voucher_redeem_code in html
        assert "NEW" in html
        assert any(part.get("content_id") == "tamatem-plus-logo" for part in payload["attachments"])
        assert any(part.get("content_id") == "order-item-image" for part in payload["attachments"])

    @override_settings(SENDGRID_API_KEY="sg-test", SENDGRID_FROM_EMAIL="store@example.com")
    @patch("orders.mail.SendGridAPIClient")
    def test_blank_email_does_not_send(self, mock_client, inline_email_threads, auth_client, product):
        response = auth_client.post("/api/orders/", {"product": product.id}, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        mock_client.assert_not_called()

    @override_settings(SENDGRID_API_KEY="", SENDGRID_FROM_EMAIL="store@example.com")
    @patch("orders.mail.SendGridAPIClient")
    def test_missing_api_key_does_not_send(self, mock_client, inline_email_threads, email_auth_client, product):
        response = email_auth_client.post("/api/orders/", {"product": product.id}, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        mock_client.assert_not_called()

    @override_settings(SENDGRID_API_KEY="sg-test", SENDGRID_FROM_EMAIL="store@example.com")
    @patch("orders.mail.SendGridAPIClient")
    def test_sendgrid_failure_does_not_change_order(
        self, mock_client, inline_email_threads, email_auth_client, product
    ):
        mock_client.return_value.send.side_effect = RuntimeError("sendgrid down")
        response = email_auth_client.post("/api/orders/", {"product": product.id}, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        order = Order.objects.get(pk=response.data["id"])
        assert order.voucher_status == Order.VoucherStatus.NEW
        assert order.voucher_redeem_code


def test_item_image_path_for_mapped_and_unknown_titles():
    assert item_image_path("Sword of Valor") is not None
    assert item_image_path("Unknown Relic") is None
