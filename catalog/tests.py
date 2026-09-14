import pytest
from rest_framework import status

from catalog import store
from catalog.models import Product


@pytest.fixture
def seed_products(db):
    # 60 rows (30 JO / 30 SA) so page_size cap (50) is actually exercised
    for i in range(1, 61):
        Product.objects.create(
            external_id=i,
            title=f"Item {i}",
            description="desc",
            price="9.99",
            location="JO" if i % 2 else "SA",
        )
    store.load_products()  # views read from the in-process map, not the DB
    yield


class TestAuth:
    def test_login_valid_returns_tokens(self, api_client, user):
        response = api_client.post("/api/auth/login/", {"username": "alice", "password": "pass12345"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data and "refresh" in response.data

    def test_login_invalid_returns_401(self, api_client, user):
        response = api_client.post("/api/auth/login/", {"username": "alice", "password": "wrong"}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestProducts:
    def test_list_requires_auth(self, api_client, seed_products):
        response = api_client.get("/api/products/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_is_paginated(self, auth_client, seed_products):
        response = auth_client.get("/api/products/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 60
        assert len(response.data["results"]) == 10

    def test_list_filters_by_location(self, auth_client, seed_products):
        response = auth_client.get("/api/products/", {"location": "JO"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 30
        assert all(item["location"] == "JO" for item in response.data["results"])

    def test_detail_missing_returns_404(self, auth_client, seed_products):
        response = auth_client.get("/api/products/999999/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_page_size_is_capped(self, auth_client, seed_products):
        response = auth_client.get("/api/products/", {"page_size": 1000})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 50
