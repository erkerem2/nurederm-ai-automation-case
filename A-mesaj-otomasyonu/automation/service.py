from dataclasses import dataclass, replace

from .classifiers import Classifier
from .domain import CartError, Message, ProviderError, Ticket, Topic
from .orders import OrderClient, extract_order_ids, format_owned_order
from .products import CatalogError, ProductClient, matching_products


@dataclass(frozen=True)
class ProcessResult:
    ticket: Ticket
    error_code: str | None = None


class MessageService:
    def __init__(self, classifier: Classifier, orders: OrderClient, products: ProductClient | None = None):
        self.classifier = classifier
        self.orders = orders
        self.products = products

    def process(self, message: Message) -> ProcessResult:
        try:
            classification = self.classifier.classify(message)
        except ProviderError as error:
            return ProcessResult(Ticket(
                message.id, Topic.OTHER, True,
                "Talebinizin değerlendirilmesi için sizi müşteri temsilcimize yönlendiriyoruz.",
                f"Sınıflandırma tamamlanamadı; temsilci incelemesi gerekiyor. Hata: {error}.",
            ), str(error))

        topic = classification.topic
        if topic == Topic.SENSITIVE:
            ticket = Ticket(message.id, topic, True,
                            "Yaşadığınız durumun değerlendirilmesi için sizi müşteri temsilcimize yönlendiriyoruz.",
                            "Hassas konu; teşhis, tedavi veya ürün önerisi üretilmedi.")
        elif topic == Topic.RETURN:
            ticket = Ticket(message.id, topic, True,
                            "İade veya şikâyet talebiniz için sizi müşteri temsilcimize yönlendiriyoruz.",
                            "İade/şikâyet işlemi temsilci tarafından değerlendirilmeli.")
        elif topic == Topic.ORDER:
            result = self.process_order(message)
            ticket = result.ticket
            if classification.secondary_topics:
                ticket = self.add_secondary(ticket, classification.secondary_topics)
            return ProcessResult(self.add_source(ticket), result.error_code)
        elif topic == Topic.SPAM:
            ticket = Ticket(message.id, topic, False, "", "İstenmeyen reklam; yanıt üretilmedi, bağlantı açılmadı.")
        elif topic in (Topic.PRODUCT, Topic.PRICE) and classification.product_query and self.products:
            result = self.process_catalog(message, topic, classification.product_query)
            ticket = result.ticket
            if classification.secondary_topics:
                ticket = self.add_secondary(ticket, classification.secondary_topics)
            return ProcessResult(self.add_source(ticket), result.error_code)
        else:
            ticket = Ticket(message.id, topic, True,
                            "Sorunuz için doğrulanmış bilgiyi paylaşabilmesi adına sizi müşteri temsilcimize yönlendiriyoruz.",
                            "Ürün, fiyat veya mağaza politikası için doğrulanmış bilgi kaynağı bulunmuyor.")
        if classification.secondary_topics:
            ticket = self.add_secondary(ticket, classification.secondary_topics)
        return ProcessResult(self.add_source(ticket))

    def process_order(self, message: Message) -> ProcessResult:
        order_ids = extract_order_ids(message.text)
        if len(order_ids) != 1:
            draft = ("Siparişinizi kontrol edebilmemiz için sipariş numaranızı paylaşır mısınız?"
                     if not order_ids else "Birden fazla sipariş numarası görüyoruz. Hangi siparişi kontrol etmemizi istersiniz?")
            return ProcessResult(Ticket(message.id, Topic.ORDER, True, draft,
                                        "Tek bir sipariş numarası belirlenemedi; API sorgusu yapılmadı."))
        order_id = order_ids[0]
        try:
            cart = self.orders.fetch(order_id)
            if cart is None:
                return ProcessResult(Ticket(message.id, Topic.ORDER, True,
                                            "Bu numarayla sipariş kaydı bulunamadı. Lütfen sipariş numaranızı kontrol edin; temsilcimiz yardımcı olacak.",
                                            "Sipariş API'si 404 döndürdü."))
            draft = format_owned_order(cart, order_id, message.customer_id)
            if draft is None:
                return ProcessResult(Ticket(message.id, Topic.ORDER, True,
                                            "Siparişin hesabınıza ait olduğunu doğrulayamadık. Yardımcı olması için sizi müşteri temsilcimize yönlendiriyoruz.",
                                            "Sahiplik eşleşmedi; sipariş ayrıntıları paylaşılmadı."))
            return ProcessResult(Ticket(message.id, Topic.ORDER, False, draft,
                                        "Sipariş sahipliği doğrulandı. Kaynakta kargo veya teslimat bilgisi yok."))
        except CartError as error:
            return ProcessResult(Ticket(message.id, Topic.ORDER, True,
                                        "Sipariş bilgilerinizi şu anda doğrulayamıyoruz. Yardımcı olması için sizi müşteri temsilcimize yönlendiriyoruz.",
                                        f"Sipariş sorgusu tamamlanamadı. Hata: {error}."), str(error))

    def process_catalog(self, message: Message, topic: Topic, query: str) -> ProcessResult:
        # Catalog data can list products and prices, but never answers suitability or ingredient questions.
        handoff_note = "Ürün uygunluğu, içerik ve güncel fiyat temsilci tarafından teyit edilmeli."
        try:
            matches = matching_products(self.products.search(query), query)
        except CatalogError as error:
            return ProcessResult(Ticket(
                message.id, topic, True,
                "Sorunuz için doğrulanmış bilgiyi paylaşabilmesi adına sizi müşteri temsilcimize yönlendiriyoruz.",
                f"Ürün araması tamamlanamadı (arama: '{query}'). Hata: {error}.",
            ), str(error))
        if not matches:
            return ProcessResult(Ticket(
                message.id, topic, True,
                "Kataloğumuzda bu ürünle eşleşen bir kayıt bulamadık. Sizi müşteri temsilcimize yönlendiriyoruz.",
                f"Ürün araması: '{query}' için kozmetik kategorisinde eşleşme yok. {handoff_note}",
            ))
        listed = ", ".join(f"{title} (fiyat: {price})" for title, price in matches)
        return ProcessResult(Ticket(
            message.id, topic, True,
            f"Kataloğumuzda bulunan ilgili ürünler: {listed}. Fiyatlar test API'sinden alınmıştır, para birimi belirtilmemiştir. "
            "Sorunuzun ayrıntıları için sizi müşteri temsilcimize yönlendiriyoruz.",
            f"Ürün araması: '{query}' için {len(matches)} eşleşme taslağa eklendi. {handoff_note}",
        ))

    def add_source(self, ticket: Ticket) -> Ticket:
        source = ("Manuel demo sınıflandırması; çalışma anında LLM kullanılmadı."
                  if self.classifier.name == "manual" else f"Sınıflandırma sağlayıcısı: {self.classifier.name}.")
        return replace(ticket, note=f"{ticket.note} {source}")

    @staticmethod
    def add_secondary(ticket: Ticket, secondary: tuple[Topic, ...]) -> Ticket:
        note = f"{ticket.note} Ek konular temsilciye iletildi: {', '.join(secondary)}."
        draft = ticket.draft
        if ticket.topic not in (Topic.SENSITIVE, Topic.RETURN):
            draft += " Mesajınızdaki diğer sorular için de sizi temsilcimize yönlendiriyoruz."
        return replace(ticket, handoff=True, draft=draft, note=note)
