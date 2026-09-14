import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def _clear_cache():
    # login is throttled; reset between tests so one test's attempts don't trip another's limit
    cache.clear()
    yield


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="alice", password="pass12345")


@pytest.fixture
def other_user(db):
    return get_user_model().objects.create_user(username="bob", password="pass12345")


def _login(client, username, password):
    response = client.post("/api/auth/login/", {"username": username, "password": password}, format="json")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return client


@pytest.fixture
def auth_client(api_client, user):
    return _login(api_client, "alice", "pass12345")


@pytest.fixture
def other_auth_client(other_user):
    return _login(APIClient(), "bob", "pass12345")
