"""Widget-state persistence across page switches.

Streamlit drops a widget's stored value when a run doesn't render that
widget, which in a multi-section app means every filter resets the moment
you visit a section that doesn't have it. Re-asserting the key on each run
keeps the value alive, so the sidebar filters genuinely carry over.
"""

from __future__ import annotations

import streamlit as st


def keep(key: str, default=None) -> str:
    """Seed and preserve a widget's session-state value; returns the key.

    Use as the widget's `key=` and omit `value=`/`default=`: when a key
    already exists in session state Streamlit takes the value from there,
    and passing both would be ambiguous.
    """
    if key not in st.session_state:
        if default is not None:
            st.session_state[key] = default
    else:
        # Re-assert so Streamlit doesn't garbage-collect it on a run that
        # doesn't render this widget.
        st.session_state[key] = st.session_state[key]
    return key
