import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import Config
from core.interfaces import EmailSender


# ── HTML rendering (pure functions, no I/O) ─────────────────────────────────

def _product_card_html(product: dict) -> str:
    price_str = f"S${product['price_sgd']:.2f}" if product.get("price_sgd") is not None else ""
    rating_str = f"⭐ {product['rating']:.1f}" if product.get("rating") else ""
    img_tag = (
        f'<img src="{product["image_url"]}" width="120" height="120" '
        'style="object-fit:cover;border-radius:6px;" />'
        if product.get("image_url")
        else ""
    )
    return (
        f'<td style="padding:8px;vertical-align:top;text-align:center;width:160px;">'
        f'<a href="{product["product_url"]}" style="text-decoration:none;color:inherit;">'
        f"{img_tag}"
        f'<p style="margin:6px 0 2px;font-size:13px;color:#333;line-height:1.3;">'
        f"{product['name'][:60]}</p>"
        f'<p style="margin:0;font-size:14px;font-weight:bold;color:#e05c00;">{price_str}</p>'
        f'<p style="margin:2px 0 6px;font-size:12px;color:#888;">{rating_str}</p>'
        f'<span style="display:inline-block;padding:5px 12px;background:#ee4d2d;color:white;'
        f'border-radius:4px;font-size:12px;">View on Shopee</span>'
        f"</a></td>"
    )


def _build_html(chosen_style: str, shopee_results: dict[str, list]) -> str:
    sections = []
    for category, products in shopee_results.items():
        cards = "".join(_product_card_html(p) for p in products)
        sections.append(
            f'<h3 style="margin:20px 0 8px;color:#444;">{category}</h3>'
            f'<table cellpadding="0" cellspacing="0" style="border-collapse:collapse;">'
            f"<tr>{cards}</tr></table>"
        )

    return (
        '<html><body style="font-family:Arial,sans-serif;max-width:700px;margin:auto;padding:20px;">'
        '<div style="background:#f8f4f0;padding:24px;border-radius:12px;text-align:center;">'
        '<h1 style="color:#222;margin:0 0 4px;">🏠 Your RoomGenie Design</h1>'
        f'<p style="color:#666;margin:0;font-size:16px;">{chosen_style} Style</p>'
        "</div>"
        '<div style="margin:24px 0;text-align:center;">'
        '<img src="cid:room_design" alt="Your redesigned room" '
        'style="max-width:100%;border-radius:10px;box-shadow:0 4px 16px rgba(0,0,0,0.15);" />'
        "</div>"
        '<h2 style="color:#222;border-bottom:2px solid #ee4d2d;padding-bottom:8px;">🛒 Shop the Look</h2>'
        + "".join(sections)
        + '<div style="margin-top:32px;padding:16px;background:#fff8f6;border-radius:8px;'
        'font-size:12px;color:#999;text-align:center;">'
        "Prices from Shopee SG at time of generation.</div>"
        "</body></html>"
    )


# ── SMTP sender ──────────────────────────────────────────────────────────────

class GmailEmailSender(EmailSender):
    """Implements EmailSender via Gmail SMTP SSL on port 465."""

    def __init__(self, config: Config) -> None:
        self._config = config

    def send(
        self,
        to_email: str,
        chosen_style: str,
        image_bytes: bytes,
        shopee_results: dict[str, list],
    ) -> None:
        msg = MIMEMultipart("related")
        msg["Subject"] = f"Your RoomGenie Design — {chosen_style} Style 🏠"
        msg["From"] = self._config.gmail_sender
        msg["To"] = to_email

        msg.attach(MIMEText(_build_html(chosen_style, shopee_results), "html"))

        img_part = MIMEImage(image_bytes, _subtype="jpeg")
        img_part.add_header("Content-ID", "<room_design>")
        img_part.add_header("Content-Disposition", "inline", filename="room_design.jpg")
        msg.attach(img_part)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(self._config.gmail_sender, self._config.gmail_password)
            server.sendmail(self._config.gmail_sender, to_email, msg.as_string())
