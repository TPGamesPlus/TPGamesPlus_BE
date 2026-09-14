from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """Default pagination: page_size=10, capped at 50 to prevent unbounded result sets."""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50
