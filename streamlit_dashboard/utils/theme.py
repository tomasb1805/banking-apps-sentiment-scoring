"""Palettes, global theming and Plotly styling for the Friction Ledger.

LIGHT is the project's canonical brand palette -- the same hex codes used in
the PDF/Word report (make_charts.py, build_report.py) and the custom Tableau
palette, so a reader flipping between the report, the Tableau workbook and
this app sees one visual system.

DARK is not an automatic flip of it. It is a separately chosen set, softer
than the first dark variant this app shipped: the surface is a dark slate
rather than near-black and the text sits below pure white, so the page reads
calm instead of glaring. The two series colours were then chosen by running
the categorical-palette validator against that surface rather than by eye,
because the obvious "just lighten the brand colours" approach failed: a pale
navy and a bright teal sit too close together in colour space (normal-vision
ΔE 12.5, below the 15 floor) and are genuinely hard to tell apart. The pair
below passes every check -- lightness band, chroma floor, colour-blind
separation, normal-vision separation and contrast against the surface --
while staying recognisably "navy for TradBank, teal for NeoBank".

Theming is applied globally, not per chart. `apply_theme()` runs once in
dashboard.py: it renders the Appearance control, injects CSS that repaints
Streamlit's own chrome, and stashes the palette for the views to read via
`current_palette()`. That is what makes Light/Dark change the whole page
rather than only the figures.
"""

from __future__ import annotations

import streamlit as st

LIGHT = {
    "navy": "#1F3A5F",   # Traditional banks / TradBank
    "teal": "#2A9D8F",   # Neobanks / NeoBank
    "rust": "#C0533A",   # Negative-direction accent
    "gold": "#C9973A",   # Secondary accent
    "grey": "#8A8A8A",   # Neutral / fallback
    "ink": "#1A1A1A",    # Body text
    "muted": "#5A5A5A",  # Secondary text, reference marks
    "rule": "#D8D8D8",   # Gridlines / dividers
    "panel": "#F4F5F7",  # Sidebar / panel background
    "bg": "#FFFFFF",     # Page + figure background
}

DARK = {
    "navy": "#2D76A3",   # validated against the dark surface, not eyeballed
    "teal": "#3CA694",
    "rust": "#C77B5E",
    "gold": "#C0A15F",
    "grey": "#8D95A2",
    "ink": "#D5DAE3",    # below pure white on purpose -- less glare
    "muted": "#97A0AE",
    "rule": "#2E3542",
    "panel": "#222836",
    "bg": "#1A1F27",     # dark slate rather than near-black
}

APPEARANCE_KEY = "appearance"
_PALETTE_KEY = "_active_palette"


def _detect_dark() -> bool:
    """True if Streamlit reports the viewer's browser is in dark mode.

    `st.context.theme` only exists on newer Streamlit versions and can raise
    outside a script run, so every failure mode falls back to light.
    """
    try:
        ctx = getattr(st, "context", None)
        if ctx is None:
            return False
        return getattr(getattr(ctx, "theme", None), "type", "light") == "dark"
    except Exception:
        return False


def apply_theme() -> dict:
    """Render the Appearance control, theme the whole page, return the palette.

    Called once, from dashboard.py, so the control is re-rendered on every
    run no matter which view is showing. That is deliberate: Streamlit drops
    widget state for widgets that a run doesn't render, which is why the
    earlier per-page version of this control reset itself to Auto whenever
    you switched sections.
    """
    st.sidebar.radio(
        "Appearance",
        options=["Auto", "Light", "Dark"],
        index=0,
        horizontal=True,
        key=APPEARANCE_KEY,
        help=(
            "Auto follows your browser's dark-mode setting. Light and Dark "
            "override it for the whole dashboard and stay put as you move "
            "between sections."
        ),
    )
    choice = st.session_state.get(APPEARANCE_KEY, "Auto")
    dark = choice == "Dark" or (choice == "Auto" and _detect_dark())
    palette = DARK if dark else LIGHT
    st.session_state[_PALETTE_KEY] = palette
    _inject_css(palette, dark)
    return palette


def current_palette() -> dict:
    """The palette chosen by apply_theme(), for views to read."""
    return st.session_state.get(_PALETTE_KEY, LIGHT)


def _inject_css(p: dict, dark: bool) -> None:
    """Repaint Streamlit's own chrome to match the chosen palette.

    Streamlit has no runtime theme API, so a page-level theme has to be CSS.
    Selectors are the stable data-testid hooks plus plain element names; the
    .fl-table rules style the Release Friction table, which is rendered as
    HTML precisely so it can follow the theme (st.dataframe renders in a
    canvas grid that ignores page CSS and would stay light on a dark page).
    """
    st.markdown(
        f"""
        <style>
        :root {{ color-scheme: {"dark" if dark else "light"}; }}
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stHeader"] {{ background-color: {p["bg"]}; }}
        [data-testid="stSidebar"],
        [data-testid="stSidebar"] > div:first-child {{ background-color: {p["panel"]}; }}
        h1, h2, h3, h4, h5, h6, p, li, label,
        [data-testid="stMarkdownContainer"],
        [data-testid="stMetricValue"] {{ color: {p["ink"]} !important; }}
        [data-testid="stCaptionContainer"],
        [data-testid="stCaptionContainer"] *,
        [data-testid="stMetricLabel"] {{ color: {p["muted"]} !important; }}
        hr {{ border-color: {p["rule"]} !important; }}

        .fl-table {{
            width: 100%; border-collapse: collapse; font-size: 0.86rem;
            color: {p["ink"]}; margin-top: 0.4rem;
        }}
        .fl-table th {{
            text-align: left; font-weight: 600; color: {p["muted"]};
            border-bottom: 1px solid {p["rule"]}; padding: 0.4rem 0.6rem;
            white-space: nowrap;
        }}
        .fl-table td {{
            border-bottom: 1px solid {p["rule"]}; padding: 0.35rem 0.6rem;
            white-space: nowrap;
        }}
        .fl-table tr:hover td {{ background-color: {p["panel"]}; }}
        .fl-table td:nth-child(n+5), .fl-table th:nth-child(n+5) {{
            text-align: right; font-variant-numeric: tabular-nums;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def provider_colors(p: dict) -> dict:
    """Provider-group colour mapping for the active palette."""
    return {"TradBank": p["navy"], "NeoBank": p["teal"]}


def style(fig, p: dict):
    """Apply the shared layout to a Plotly figure for the active palette."""
    fig.update_layout(
        font=dict(family="Helvetica, Arial, sans-serif", color=p["ink"], size=13),
        plot_bgcolor=p["bg"],
        paper_bgcolor=p["bg"],
        margin=dict(l=10, r=10, t=50, b=10),
        hoverlabel=dict(bgcolor=p["panel"], font_size=12, font_color=p["ink"]),
        legend=dict(font=dict(color=p["ink"])),
    )
    axis_kwargs = dict(
        gridcolor=p["rule"],
        zeroline=False,
        linecolor=p["rule"],
        tickfont=dict(color=p["ink"]),
        title_font=dict(color=p["ink"]),
    )
    fig.update_xaxes(**axis_kwargs)
    fig.update_yaxes(**axis_kwargs)

    # Subplot titles and add_hline/add_vline labels are annotations, which
    # keep Plotly's default dark text unless recoloured explicitly.
    for annotation in fig.layout.annotations or []:
        annotation.font.color = p["ink"]

    return fig
