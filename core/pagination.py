from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """Default pagination: page_size=10, capped at 50 to prevent unbounded result sets."""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

    def get_paginated_response_schema(self, schema):
        response = super().get_paginated_response_schema(schema)
        response["properties"]["facets"] = {
            "type": "object",
            "properties": {
                "titles": {"type": "array", "items": {"type": "string"}},
                "min_price": {"type": "string", "nullable": True},
                "max_price": {"type": "string", "nullable": True},
            },
        }
        return response
