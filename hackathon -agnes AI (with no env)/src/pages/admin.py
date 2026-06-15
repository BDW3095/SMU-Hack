import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

from db import get_stats

st.set_page_config(page_title="Admin — RoomGenie", page_icon="📊", layout="wide")

_ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")

# ── Auth gate ────────────────────────────────────────────────────────────────
if "admin_authed" not in st.session_state:
    st.session_state.admin_authed = False

if not st.session_state.admin_authed:
    st.title("🔒 Admin Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login", type="primary"):
        if username == _ADMIN_USERNAME and password == _ADMIN_PASSWORD:
            st.session_state.admin_authed = True
            st.rerun()
        else:
            st.error("Incorrect username or password.")
    st.stop()

# ── Dashboard ────────────────────────────────────────────────────────────────
st.title("📊 RoomGenie — Click Analytics")
st.caption("Shopee product click data for monetisation reporting")

col_refresh, col_logout = st.columns([6, 1])
with col_refresh:
    if st.button("🔄 Refresh"):
        st.rerun()
with col_logout:
    if st.button("Logout"):
        st.session_state.admin_authed = False
        st.rerun()

stats = get_stats()

# ── KPI row ──────────────────────────────────────────────────────────────────
k1, k2, k3 = st.columns(3)
k1.metric("Total Clicks", stats["total"])
k2.metric("Categories Tracked", len(stats["by_category"]))
k3.metric("Unique Products Clicked", len(stats["by_product"]))

st.markdown("---")

# ── Clicks per day ───────────────────────────────────────────────────────────
if stats["by_day"]:
    st.subheader("Clicks per Day")
    # Reverse to show chronological order
    day_data = {row["day"]: row["clicks"] for row in reversed(stats["by_day"])}
    st.bar_chart(day_data)
else:
    st.info("No click data yet. Send users to the main app!")

# ── Clicks by category ───────────────────────────────────────────────────────
if stats["by_category"]:
    st.subheader("Clicks by Category")
    cat_data = {row["category"]: row["clicks"] for row in stats["by_category"]}
    st.bar_chart(cat_data)

# ── Top clicked products ─────────────────────────────────────────────────────
if stats["by_product"]:
    st.subheader("Top Clicked Products")
    st.dataframe(
        stats["by_product"],
        column_order=["product_name", "category", "clicks", "product_url"],
        use_container_width=True,
    )

# ── Recent clicks ────────────────────────────────────────────────────────────
if stats["recent"]:
    st.subheader("Recent Clicks (last 50)")
    st.dataframe(stats["recent"], use_container_width=True)

    csv_rows = ["timestamp,product_name,category,product_url,session_id"]
    for r in stats["recent"]:
        csv_rows.append(
            f'"{r["timestamp"]}","{r["product_name"]}","{r["category"]}",'
            f'"{r["product_url"]}","{r["session_id"]}"'
        )
    st.download_button(
        "⬇️ Export CSV",
        data="\n".join(csv_rows).encode(),
        file_name="roomgenie_clicks.csv",
        mime="text/csv",
    )
