import sys
import os
import base64
sys.path.insert(0, os.path.dirname(__file__))

from concurrent.futures import ThreadPoolExecutor

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")


def _loading_media_html() -> str:
    """Return an HTML snippet for the loading screen media.

    Checks assets/ (project root) for loading.mp4, loading.gif, loading.png,
    loading.jpg in that order. Encodes the first match as a base64 data URL so
    Streamlit can render it inline. Falls back to a pulsing emoji if no file found.
    """
    candidates = [
        ("loading.mp4", "video/mp4"),
        ("loading.gif", "image/gif"),
        ("loading.png", "image/png"),
        ("loading.jpg", "image/jpeg"),
    ]
    for fname, mime in candidates:
        fpath = os.path.join(_ASSETS_DIR, fname)
        if os.path.exists(fpath):
            with open(fpath, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            if mime == "video/mp4":
                return (
                    f'<video autoplay loop muted playsinline '
                    f'style="width:100%;max-width:360px;border-radius:12px;margin-bottom:12px;" '
                    f'src="data:{mime};base64,{data}"></video>'
                )
            return (
                f'<img src="data:{mime};base64,{data}" '
                f'style="width:100%;max-width:360px;border-radius:12px;margin-bottom:12px;" />'
            )
    # Fallback: CSS-animated emoji
    return '<div style="font-size:52px;animation:pulse 1.5s ease-in-out infinite;margin-bottom:12px;">🎨</div>'

import uuid
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

load_dotenv()

from config import Config
from clients.agnes_client import AgnesClient
from clients.scrapeless_client import ScrapelessClient
from agents.image_agent import ImageAgent, AgnesImageProvider, STYLES
from agents.furniture_agent import AgnesFurnitureProvider
from services.shopee_service import ShopeeProductSearchProvider
from services.email_service import GmailEmailSender
from ui.context_form import ContextForm
from utils.image_utils import normalize_to_jpeg
from db import init_db, log_click

# ── Dependency injection — wire concrete implementations to abstractions ─────
_config = Config.from_env()
_agnes_client = AgnesClient(_config)
_scrapeless_client = ScrapelessClient(_config)

_image_agent = ImageAgent(AgnesImageProvider(_agnes_client))
_furniture_provider = AgnesFurnitureProvider(_agnes_client)
_shopee_provider = ShopeeProductSearchProvider(_scrapeless_client)
_email_sender = GmailEmailSender(_config)

# ── App config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="RoomGenie", page_icon="🏠", layout="wide")

for key, default in {
    "step": 1,
    "image_bytes": None,
    "context": None,
    "styled_images": None,
    "furniture_list": None,
    "shopee_results": None,
    "chosen_style": None,
    "chosen_image": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

init_db()


def go_to(step: int) -> None:
    st.session_state.step = step
    st.rerun()


# ── Progress bar ─────────────────────────────────────────────────────────────
STEP_LABELS = ["Upload", "Context", "Generate", "Select", "Email"]
for i, (col, label) in enumerate(zip(st.columns(len(STEP_LABELS)), STEP_LABELS)):
    active = st.session_state.step == i + 1
    done = st.session_state.step > i + 1
    colour = "#ee4d2d" if active else ("#4caf50" if done else "#ddd")
    col.markdown(
        f"<div style='text-align:center;padding:6px 0;border-bottom:3px solid {colour};"
        f"font-size:13px;color:{colour};font-weight:{'bold' if active else 'normal'}'>"
        f"{'✓ ' if done else ''}{i + 1}. {label}</div>",
        unsafe_allow_html=True,
    )

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Upload
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.step == 1:
    st.title("🏠 RoomGenie")
    st.subheader("Step 1 — Upload your room photo")
    st.caption("We'll transform it into 4 beautiful redesigns and find matching furniture on Shopee.")

    uploaded = st.file_uploader(
        "Choose a photo", type=["jpg", "jpeg", "png", "webp"], label_visibility="collapsed"
    )
    if uploaded:
        st.session_state.image_bytes = normalize_to_jpeg(uploaded.read())
        st.image(st.session_state.image_bytes, caption="Your room", width='stretch')
        st.button("Next →", type="primary", on_click=lambda: go_to(2))

# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Context form
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 2:
    st.subheader("Step 2 — What do you want in your room?")
    col_img, col_form = st.columns([1, 2])
    with col_img:
        st.image(st.session_state.image_bytes, caption="Your room", width='stretch')
    with col_form:
        context = ContextForm().render()
        if context:
            st.session_state.context = context
            st.session_state.styled_images = None
            st.session_state.furniture_list = None
            st.session_state.shopee_results = None
            go_to(3)

# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Generate designs + Shopee concurrently
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 3:
    st.subheader("Step 3 — Your 4 Design Options")

    if st.session_state.styled_images is None:
        load_col_photo, load_col_card = st.columns([1, 2])
        with load_col_photo:
            st.image(st.session_state.image_bytes, caption="Your room", width='stretch')
        with load_col_card:
            status = st.empty()
            status.markdown(
                f"""
                <div style="text-align:center;padding:40px 32px;background:#fafafa;
                            border-radius:16px;border:1px solid #eee;">
                  {_loading_media_html()}
                  <h3 style="margin:0 0 6px;color:#333;">Designing your room…</h3>
                  <p style="color:#888;font-size:14px;line-height:1.6;margin:0 0 18px;">
                    Generating 4 style variants &amp; finding Shopee deals simultaneously.<br>
                    <strong>This takes 1–3 minutes</strong> — hang tight!
                  </p>
                  <div style="font-size:13px;color:#bbb;letter-spacing:0.5px;">
                    Minimalist &nbsp;·&nbsp; Scandinavian &nbsp;·&nbsp;
                    Modern Industrial &nbsp;·&nbsp; Tropical / Rattan
                  </div>
                </div>
                <style>
                  @keyframes pulse {{
                    0%, 100% {{ opacity: 1; transform: scale(1); }}
                    50%       {{ opacity: 0.55; transform: scale(1.15); }}
                  }}
                </style>
                """,
                unsafe_allow_html=True,
            )

        # Capture session state values before entering threads —
        # st.session_state is not accessible from ThreadPoolExecutor workers.
        _image_bytes = st.session_state.image_bytes
        _context = st.session_state.context

        def _generate_images() -> dict[str, bytes]:
            return _image_agent.generate_all_styles(_image_bytes, _context)

        def _furniture_then_shopee() -> tuple[list, dict]:
            items = _furniture_provider.generate_list(_context)
            results = _shopee_provider.search_all(items)
            return items, results

        try:
            with ThreadPoolExecutor(max_workers=2) as ex:
                img_future = ex.submit(_generate_images)
                shop_future = ex.submit(_furniture_then_shopee)
            st.session_state.styled_images = img_future.result()
            st.session_state.furniture_list, st.session_state.shopee_results = shop_future.result()
            status.empty()
        except Exception as e:
            st.error(f"Design generation failed: {e}. Please try again.")
            if st.button("← Back"):
                go_to(2)
            st.stop()

    style_names = list(STYLES.keys())
    for row_styles in [style_names[:2], style_names[2:]]:
        for col, style_name in zip(st.columns(2), row_styles):
            img_bytes = st.session_state.styled_images.get(style_name)
            if img_bytes:
                with col:
                    st.image(img_bytes, caption=style_name, width='stretch')
                    if st.button(f"Choose {style_name}", key=f"pick_{style_name}", use_container_width=True):
                        st.session_state.chosen_style = style_name
                        st.session_state.chosen_image = img_bytes
                        go_to(4)

    if st.button("← Change preferences"):
        go_to(2)

# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Review + shopping list + email
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 4:
    st.subheader(f"Step 4 — Your {st.session_state.chosen_style} Design")

    for col, (img, caption) in zip(
        st.columns(2),
        [(st.session_state.image_bytes, "Before"),
         (st.session_state.chosen_image, f"After — {st.session_state.chosen_style}")],
    ):
        with col:
            st.image(img, caption=caption, width='stretch')

    st.markdown("---")
    st.subheader("🛒 Shop the Look")
    categories = list((st.session_state.shopee_results or {}).keys())
    if categories:
        tabs = st.tabs(categories)
        for tab, category in zip(tabs, categories):
            products = st.session_state.shopee_results[category]
            with tab:
                if not products:
                    st.caption("No products found — search manually on Shopee.")
                else:
                    p_cols = st.columns(min(len(products), 3))
                    for i, product in enumerate(products[:3]):
                        with p_cols[i]:
                            if product.get("image_url"):
                                st.image(product["image_url"], width=130)
                            name_display = product["name"][:55] + ("…" if len(product["name"]) > 55 else "")
                            st.caption(name_display)
                            if product.get("price_sgd") is not None:
                                st.markdown(f"**S${product['price_sgd']:.2f}**")
                            if product.get("rating"):
                                st.caption(f"⭐ {product['rating']:.1f}")
                            if st.button(
                                "View on Shopee →",
                                key=f"shopee_{category}_{i}",
                                use_container_width=True,
                            ):
                                log_click(
                                    product_id=product["product_url"],
                                    product_name=product["name"],
                                    category=category,
                                    product_url=product["product_url"],
                                    session_id=st.session_state.session_id,
                                )
                                components.html(
                                    f'<script>window.top.open("{product["product_url"]}", "_blank");</script>',
                                    height=0,
                                )
    else:
        st.caption("No shopping results available.")

    st.markdown("---")
    st.subheader("📧 Get this design by email")
    email = st.text_input("Your email address", placeholder="you@example.com")
    send_col, back_col = st.columns([3, 1])
    with send_col:
        if st.button("Send to my email", type="primary", use_container_width=True):
            if not email or "@" not in email:
                st.warning("Please enter a valid email address.")
            else:
                with st.spinner("Sending…"):
                    try:
                        _email_sender.send(
                            to_email=email,
                            chosen_style=st.session_state.chosen_style,
                            image_bytes=st.session_state.chosen_image,
                            shopee_results=st.session_state.shopee_results or {},
                        )
                        go_to(5)
                    except Exception as e:
                        st.error(f"Email failed: {e}. Check GMAIL_APP_PASSWORD in .env.")
    with back_col:
        if st.button("← Pick another style", use_container_width=True):
            go_to(3)

# ══════════════════════════════════════════════════════════════════════════════
# STEP 5 — Done
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 5:
    st.balloons()
    st.success("✅ Your design has been sent! Check your inbox.")
    st.image(st.session_state.chosen_image, caption=f"{st.session_state.chosen_style} Style", width='stretch')
    st.markdown(f"**Style chosen:** {st.session_state.chosen_style}")

    if st.button("🏠 Design another room", type="primary"):
        for key in ["image_bytes", "context", "styled_images", "furniture_list",
                    "shopee_results", "chosen_style", "chosen_image"]:
            st.session_state[key] = None
        st.session_state.step = 1
        st.rerun()
