"""The Friction Ledger — Streamlit portfolio dashboard.

Entry point. Run with:  streamlit run dashboard.py

This uses st.navigation rather than Streamlit's automatic pages/ directory,
for one concrete reason: with pages/, every section is its own top-level
script and anything rendered in the sidebar belongs to whichever section is
showing. That made the Appearance control reset to Auto on every section
change. Here dashboard.py runs on every interaction regardless of section,
so the theme control is rendered once, globally, and its value survives
navigation. It also lets the section titles be set explicitly instead of
being derived from filenames.
"""

from __future__ import annotations

import streamlit as st

from utils.theme import apply_theme

st.set_page_config(page_title="The Friction Ledger", page_icon="📊", layout="wide")

st.sidebar.title("The Friction Ledger")
st.sidebar.caption("UK retail banking app review analytics")

# Global, before any view renders: paints the page and fixes the palette that
# every chart in every view will read.
apply_theme()

navigation = st.navigation(
    [
        st.Page("views/home.py", title="Home", icon="📊", default=True),
        st.Page("views/sentiment_by_provider.py", title="Sentiment by Provider", icon="📈"),
        st.Page("views/complaint_drivers.py", title="Complaint Drivers", icon="🧭"),
        st.Page("views/release_friction.py", title="Release Friction", icon="🚀"),
    ]
)
navigation.run()
