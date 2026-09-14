import pytest
from rest_framework import status

from catalog import store
from catalog.models import Product
from orders.models import Order


@pytest.fixture
def product(db):
    p = Product.objects.create(external_id=1, title="Sword", description="d", price="19.99", location="JO")
    store.load_products()
    return p


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

    def test_buy_nonexistent_product_returns_400(self, auth_client):
        response = auth_client.post("/api/orders/", {"product": 999999}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_retrieve_own_order(self, auth_client, product):
        create_response = auth_client.post("/api/orders/", {"product": product.id}, format="json")
        response = auth_client.get(f"/api/orders/{create_response.data['id']}/")
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_other_users_order_returns_404(self, auth_client, other_auth_client, product):
        create_response = auth_client.post("/api/orders/", {"product": product.id}, format="json")
        response = other_auth_client.get(f"/api/orders/{create_response.data['id']}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
