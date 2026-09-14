from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


class LoginThrottle(AnonRateThrottle):
    scope = "login"


@extend_schema_view(
    post=extend_schema(
        summary="Login",
        description="Validate credentials and obtain a JWT access/refresh token pair.",
        examples=[
            OpenApiExample(
                "Valid login",
                value={"username": "demo", "password": "demoPass123!"},
                request_only=True,
            ),
            OpenApiExample(
                "Tokens issued",
                value={
                    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIs...",
                    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwi...",
                },
                response_only=True,
            ),
        ],
    ),
)
class LoginView(TokenObtainPairView):
    # DRF's global default is IsAuthenticated, which would make login unreachable without a token
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]


@extend_schema_view(
    post=extend_schema(
        summary="Refresh access token",
        description="Exchange a refresh token for a new access token.",
        examples=[
            OpenApiExample(
                "Refresh request",
                value={"refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIs..."},
                request_only=True,
            ),
            OpenApiExample(
                "New access token",
                value={"access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwi..."},
                response_only=True,
            ),
        ],
    ),
)
class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
