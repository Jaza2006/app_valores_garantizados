# login.py
"""Inicio de sesión de Seguros JR.

Uso en app.py (después de st.set_page_config):

    from login import requiere_login, boton_cerrar_sesion
    requiere_login()          # detiene la app hasta que la respuesta sea correcta
    boton_cerrar_sesion()     # botón en la barra lateral
"""
import unicodedata

import streamlit as st

PREGUNTA = "¿Quién es mi maestra favorita?"
CONTRASENA = "iris"   # respuesta correcta (no distingue mayúsculas ni acentos)
MARCA = "Seguros JR"
SUBTITULO = "Valores Garantizados"


def _normalizar(txt: str) -> str:
    """Quita acentos, espacios sobrantes y mayúsculas."""
    txt = unicodedata.normalize("NFKD", str(txt))
    return txt.encode("ascii", "ignore").decode().strip().lower()


def _pantalla_login():
    _, centro, _ = st.columns([1, 2, 1])
    with centro:
        st.markdown(
            f"<h1 style='text-align:center; margin-bottom:0;'>🫵 {MARCA} 🫵</h1>"
            f"<h3 style='text-align:center; margin-top:0;'>{SUBTITULO}</h3>",
            unsafe_allow_html=True,
        )
        st.markdown("---")
        with st.form("login"):
            respuesta = st.text_input(
                PREGUNTA, type="password", placeholder="Escribe tu respuesta"
            )
            entrar = st.form_submit_button(
                "Entrar", type="primary", use_container_width=True
            )
        if entrar:
            if _normalizar(respuesta) == _normalizar(CONTRASENA):
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("❌ Respuesta incorrecta. Intenta de nuevo.")


def requiere_login():
    """Muestra el login y detiene la app si la sesión no está iniciada."""
    if not st.session_state.get("autenticado", False):
        _pantalla_login()
        st.stop()


def boton_cerrar_sesion():
    """Botón en la barra lateral para cerrar la sesión."""
    if st.sidebar.button("🔒 Cerrar sesión"):
        st.session_state["autenticado"] = False
        st.session_state.pop("generado", None)
        st.rerun()