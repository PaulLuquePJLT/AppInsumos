import streamlit as st


def current_user() -> dict:
    return st.session_state.get("auth_user") or {}


def current_user_id(default: int = 1) -> int:
    user = current_user()
    return int(user.get("id_usuario") or default)


def is_admin() -> bool:
    return bool(current_user().get("is_admin"))
