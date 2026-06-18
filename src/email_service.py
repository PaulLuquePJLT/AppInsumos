import os
import smtplib
from email.message import EmailMessage

import streamlit as st


def _get_setting(key: str, default: str | None = None) -> str | None:
    try:
        if key in st.secrets and st.secrets[key] not in (None, ""):
            return str(st.secrets[key])
    except Exception:
        pass

    value = os.getenv(key, default)
    return str(value) if value not in (None, "") else default


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default

    return str(value).strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "si",
        "sí",
        "s",
    }


def send_email(to_email: str, subject: str, body: str) -> None:
    smtp_host = _get_setting("SMTP_HOST")
    smtp_port = int(_get_setting("SMTP_PORT", "587"))
    smtp_user = _get_setting("SMTP_USER")
    smtp_password = _get_setting("SMTP_PASSWORD")
    smtp_from = _get_setting("SMTP_FROM", smtp_user)
    smtp_use_tls = _to_bool(_get_setting("SMTP_USE_TLS", "true"), True)
    smtp_use_ssl = _to_bool(_get_setting("SMTP_USE_SSL", "false"), False)

    missing = [
        name
        for name, value in {
            "SMTP_HOST": smtp_host,
            "SMTP_USER": smtp_user,
            "SMTP_PASSWORD": smtp_password,
            "SMTP_FROM": smtp_from,
        }.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            "Faltan variables SMTP en Streamlit Secrets: " + ", ".join(missing)
        )

    message = EmailMessage()
    message["From"] = smtp_from
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    if smtp_use_ssl:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30) as server:
            server.login(smtp_user, smtp_password)
            server.send_message(message)
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            if smtp_use_tls:
                server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(message)
