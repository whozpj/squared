"""Transactional email via Resend (optional, free tier).

If no RESEND_API_KEY is configured, `send_email` is a graceful no-op that returns
False — the app works fully without email; it just doesn't send. Keeping the key
optional means the whole thing stays free until you choose to wire it up.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import get_settings

log = logging.getLogger("squared.email")


def email_configured() -> bool:
    return bool(get_settings().resend_api_key)


def send_email(to: str, subject: str, html: str) -> bool:
    """Send one email. Returns True if sent, False if skipped or failed."""
    settings = get_settings()
    if not settings.resend_api_key:
        log.info("email skipped (no RESEND_API_KEY): to=%s subject=%s", to, subject)
        return False
    try:
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={"from": settings.email_from, "to": [to], "subject": subject, "html": html},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:  # noqa: BLE001 - never let email break a request
        log.warning("email send failed to=%s: %s", to, exc)
        return False


def settle_reminder_html(from_name: str, amount_cents: int, group_name: str) -> str:
    amount = f"${amount_cents / 100:.2f}"
    url = get_settings().app_url
    return f"""
    <div style="font-family: -apple-system, system-ui, sans-serif; color: #1c1b18;">
      <h2 style="margin:0 0 8px;">You owe {from_name} {amount}</h2>
      <p style="color:#77726a; margin:0 0 16px;">
        for <strong>{group_name}</strong> on Squared.
      </p>
      <a href="{url}" style="display:inline-block; background:#1c1b18; color:#faf8f4;
        padding:10px 16px; border-radius:8px; text-decoration:none; font-weight:600;">
        Open Squared to settle up
      </a>
    </div>
    """
