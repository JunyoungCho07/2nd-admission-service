"""면접관 AI — 과학고 2차 전형(면접) 대비 서비스 진입점."""
import streamlit as st

from core.config import APP_TITLE, load_settings
from core.state import init_session_state
from ui.analysis import render_analysis
from ui.simulation import render_simulation

st.set_page_config(page_title=APP_TITLE, page_icon="🎓", layout="centered")

settings = load_settings()
init_session_state()

if st.session_state.simulation_mode:
    render_simulation(settings)
else:
    render_analysis(settings)
