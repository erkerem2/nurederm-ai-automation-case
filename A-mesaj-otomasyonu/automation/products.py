from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from .domain import AutomationError
from .http_client import HttpError, JsonClient


COSMETIC_CATEGORIES = {"beauty", "skin-care", "fragrances"}
MAX_SHOWN = 3


class CatalogError(AutomationError):
    pass


class ProductClient:
    def __init__(self, client: JsonClient):
        self.client = client

    def search(self, query: str) -> list[dict]:
        url = "https://dummyjson.com/products/search?" + urlencode(
            {"q": query, "limit": 30, "select": "title,price,category"})
        try:
            data = self.client.request("GET", url)
        except HttpError as error:
            raise CatalogError(f"catalog_{error}") from None
        products = data.get("products")
        if not isinstance(products, list):
            raise CatalogError("catalog_invalid_response")
        return products


def matching_products(products: list, query: str) -> list[tuple[str, str]]:
    """Keep cosmetics whose title contains every query word; the store search also matches
    descriptions, which returns items such as "Ice Cream" for "cream"."""
    words = query.lower().split()
    matches = []
    for product in products:
        if not isinstance(product, dict):
            raise CatalogError("catalog_invalid_product")
        title, category, price = product.get("title"), product.get("category"), product.get("price")
        if not isinstance(title, str) or not isinstance(category, str):
            raise CatalogError("catalog_invalid_product")
        if category not in COSMETIC_CATEGORIES or not all(word in title.lower() for word in words):
            continue
        if type(price) not in (int, float):
            raise CatalogError("catalog_invalid_price")
        try:
            amount = Decimal(str(price))
            if not amount.is_finite() or amount < 0:
                raise InvalidOperation
        except InvalidOperation:
            raise CatalogError("catalog_invalid_price") from None
        matches.append((title.strip(), f"{amount.quantize(Decimal('0.01')):.2f}".replace(".", ",")))
    return matches[:MAX_SHOWN]
