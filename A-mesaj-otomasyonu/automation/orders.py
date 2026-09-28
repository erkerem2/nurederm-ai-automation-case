from decimal import Decimal, InvalidOperation
import re

from .domain import CartError
from .http_client import HttpError, JsonClient


def extract_order_ids(text: str) -> list[int]:
    normalized = text.translate(str.maketrans({"İ": "i", "ı": "i", "ş": "s", "Ş": "s"})).lower()
    patterns = (
        r"\b([0-9]{1,9})\s*(?:numarali|nolu|no['’]?lu)\s+siparis\w*",
        r"\b(?:siparis\w*|order)\s*(?:(?:numarasi|numaram|no|number)\s*)?[:#-]?\s*([0-9]{1,9})\b",
        r"#\s*([0-9]{1,9})\b",
    )
    return sorted({int(match) for pattern in patterns for match in re.findall(pattern, normalized) if int(match) > 0})


class OrderClient:
    def __init__(self, client: JsonClient):
        self.client = client

    def fetch(self, order_id: int) -> dict | None:
        try:
            return self.client.request("GET", f"https://dummyjson.com/carts/{order_id}", allow_not_found=True)
        except HttpError as error:
            raise CartError(f"cart_{error}") from None


def format_owned_order(cart: dict, order_id: int, customer_id: int) -> str | None:
    if type(cart.get("userId")) is not int or type(cart.get("id")) is not int or cart["id"] != order_id:
        raise CartError("cart_invalid_identity")
    # Read no product or total fields until ownership has been checked.
    if cart["userId"] != customer_id:
        return None
    products = cart.get("products")
    if not isinstance(products, list) or not products:
        raise CartError("cart_invalid_products")
    lines = []
    for product in products:
        if not isinstance(product, dict):
            raise CartError("cart_invalid_products")
        title, quantity = product.get("title"), product.get("quantity")
        if not isinstance(title, str) or not title.strip() or len(title) > 300:
            raise CartError("cart_invalid_product_title")
        if type(quantity) is not int or quantity <= 0:
            raise CartError("cart_invalid_product_quantity")
        lines.append(f"{title.strip()} ({quantity} adet)")
    raw_total = cart.get("total")
    if type(raw_total) not in (int, float):
        raise CartError("cart_invalid_total")
    try:
        total = Decimal(str(raw_total))
        if not total.is_finite() or total < 0:
            raise InvalidOperation
        amount = f"{total.quantize(Decimal('0.01')):.2f}".replace(".", ",")
    except InvalidOperation:
        raise CartError("cart_invalid_total") from None
    return (
        f"{order_id} numaralı siparişinizdeki ürünler: {', '.join(lines)}. "
        f"Toplam tutar: {amount} (test API'si para birimi belirtmiyor). "
        "Bu kaynaktan kargo durumu veya teslim tarihi görüntülenemiyor."
    )
