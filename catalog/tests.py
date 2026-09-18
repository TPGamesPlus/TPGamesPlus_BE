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


@pytest.fixture
def seed_filter_products(db):
    rows = [
        (1, "Sword of Valor", "150.00", "JO"),
        (2, "Sword of Valor", "155.00", "JO"),
        (3, "Sword of Valor", "200.00", "SA"),
        (4, "Potion of Healing", "20.00", "JO"),
        (5, "Potion of Healing", "22.00", "JO"),
        (6, "Armor of Fortitude", "250.00", "SA"),
        (7, "Mystic Wand", "90.00", "SA"),
    ]
    for external_id, title, price, location in rows:
        Product.objects.create(
            external_id=external_id,
            title=title,
            description="desc",
            price=price,
            location=location,
        )
    store.load_products()
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

    def test_list_includes_facets(self, auth_client, seed_products):
        response = auth_client.get("/api/products/")
        assert response.status_code == status.HTTP_200_OK
        assert "facets" in response.data
        assert response.data["facets"]["min_price"] == "9.99"
        assert response.data["facets"]["max_price"] == "9.99"
        assert len(response.data["facets"]["titles"]) == 60


class TestProductFilters:
    def test_list_filters_by_title(self, auth_client, seed_filter_products):
        response = auth_client.get("/api/products/", {"title": "Sword of Valor"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 3
        assert all(item["title"] == "Sword of Valor" for item in response.data["results"])

    def test_list_filters_by_title_and_location(self, auth_client, seed_filter_products):
        response = auth_client.get("/api/products/", {"title": "Sword of Valor", "location": "JO"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2
        assert all(item["location"] == "JO" for item in response.data["results"])

    def test_list_filters_by_price_range(self, auth_client, seed_filter_products):
        response = auth_client.get("/api/products/", {"min_price": "90", "max_price": "155"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 3
        prices = {float(item["price"]) for item in response.data["results"]}
        assert prices == {90.0, 150.0, 155.0}

    def test_list_orders_by_price_asc(self, auth_client, seed_filter_products):
        response = auth_client.get("/api/products/", {"ordering": "price"})
        assert response.status_code == status.HTTP_200_OK
        prices = [float(item["price"]) for item in response.data["results"]]
        assert prices == sorted(prices)

    def test_list_orders_by_price_desc(self, auth_client, seed_filter_products):
        response = auth_client.get("/api/products/", {"ordering": "-price"})
        assert response.status_code == status.HTTP_200_OK
        prices = [float(item["price"]) for item in response.data["results"]]
        assert prices == sorted(prices, reverse=True)

    def test_facets_titles_ignore_title_and_price_params(self, auth_client, seed_filter_products):
        response = auth_client.get(
            "/api/products/",
            {
                "location": "JO",
                "title": "Potion of Healing",
                "min_price": "20",
                "max_price": "20",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["facets"]["titles"] == ["Potion of Healing", "Sword of Valor"]

    def test_facets_price_bounds_use_title_not_price_params(self, auth_client, seed_filter_products):
        response = auth_client.get(
            "/api/products/",
            {
                "location": "JO",
                "title": "Sword of Valor",
                "min_price": "155",
                "max_price": "155",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["facets"]["min_price"] == "150.00"
        assert response.data["facets"]["max_price"] == "155.00"

    def test_invalid_min_price_returns_400(self, auth_client, seed_filter_products):
        response = auth_client.get("/api/products/", {"min_price": "cheap"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == 400
        assert "min_price" in response.data["error"]["message"]

    def test_invalid_ordering_returns_400(self, auth_client, seed_filter_products):
        response = auth_client.get("/api/products/", {"ordering": "title"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "ordering" in response.data["error"]["message"]

    def test_min_greater_than_max_returns_400(self, auth_client, seed_filter_products):
        response = auth_client.get("/api/products/", {"min_price": "200", "max_price": "10"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "min_price" in response.data["error"]["message"]

    def test_filtered_list_paginates(self, auth_client, seed_filter_products):
        response = auth_client.get(
            "/api/products/",
            {"title": "Sword of Valor", "page_size": 1, "page": 2},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 3
        assert len(response.data["results"]) == 1
        assert response.data["previous"] is not None
        assert response.data["next"] is not None
