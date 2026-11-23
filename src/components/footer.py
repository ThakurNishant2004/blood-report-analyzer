"""Footer with medical disclaimer."""
import streamlit as st


def render_footer() -> None:
    st.divider()
    st.caption("⚠️ HIA is an educational project and does not provide medical advice. "
               "Always consult a qualified doctor about your results.")
