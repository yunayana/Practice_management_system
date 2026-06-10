"""
Integracja z Microsoft Entra ID (Azure AD) przez MSAL.

OAuth 2.0 Authorization Code Flow:
  1. build_auth_url()  → generuje URL logowania, zapisuje state po stronie serwera
  2. acquire_token()   → wymienia kod na token, weryfikuje state
  3. get_user_info()   → wyciąga email, imię, oid z id_token_claims
"""
from __future__ import annotations

import time
import msal
from flask import current_app

# ── Przechowywanie state po stronie serwera (zastępuje sesję Flask) ───────────
# Klucz: state (str), wartość: timestamp utworzenia
# W środowisku produkcyjnym zastąpić Redis/bazą danych.
_pending_states: dict[str, float] = {}
_STATE_TTL_SECONDS = 300  # 5 minut na ukończenie logowania


def _cleanup_states() -> None:
    """Usuwa stare, nieużyte state'y (oczyszczanie co każde wywołanie)."""
    now = time.time()
    expired = [k for k, ts in _pending_states.items() if now - ts > _STATE_TTL_SECONDS]
    for k in expired:
        del _pending_states[k]


def _build_msal_app() -> msal.ConfidentialClientApplication:
    tenant    = current_app.config["MICROSOFT_TENANT_ID"]
    authority = f"https://login.microsoftonline.com/{tenant}"
    return msal.ConfidentialClientApplication(
        client_id=current_app.config["MICROSOFT_CLIENT_ID"],
        client_credential=current_app.config["MICROSOFT_CLIENT_SECRET"],
        authority=authority,
    )


def build_auth_url() -> str:
    """
    Generuje URL do logowania Microsoft i zapisuje state po stronie serwera.
    Nie używa sesji Flask – unika problemów z ciasteczkami SameSite.
    """
    import secrets
    _cleanup_states()

    state = secrets.token_urlsafe(32)
    _pending_states[state] = time.time()   # ← serwer, nie ciasteczko

    app = _build_msal_app()
    return app.get_authorization_request_url(
        scopes=current_app.config["MICROSOFT_SCOPES"],
        redirect_uri=current_app.config["MICROSOFT_REDIRECT_URI"],
        state=state,
    )


def acquire_token(auth_code: str, state: str) -> tuple[dict | None, str | None]:
    """
    Wymienia kod autoryzacyjny na token.

    Zwraca (wynik, None) przy sukcesie lub (None, komunikat_błędu) przy błędzie.
    """
    _cleanup_states()

    # ── Weryfikacja state (ochrona CSRF – po stronie serwera) ─────────────────
    if state not in _pending_states:
        msg = (
            "Nieprawidłowy lub wygasły state OAuth. "
            "Spróbuj zalogować się od nowa (state jest ważny 5 minut)."
        )
        current_app.logger.warning("OAuth: state '%s...' nie znaleziony w _pending_states", state[:8])
        return None, msg

    del _pending_states[state]   # state jednorazowy

    # ── Wymiana kodu na token ─────────────────────────────────────────────────
    app    = _build_msal_app()
    result = app.acquire_token_by_authorization_code(
        code=auth_code,
        scopes=current_app.config["MICROSOFT_SCOPES"],
        redirect_uri=current_app.config["MICROSOFT_REDIRECT_URI"],
    )

    if "error" in result:
        error = result.get("error", "unknown_error")
        desc  = result.get("error_description", "Brak opisu błędu od Microsoft")
        current_app.logger.error("MSAL error: %s – %s", error, desc)
        return None, f"Błąd Microsoft ({error}): {desc}"

    return result, None


def get_user_info(token_result: dict) -> dict:
    """Wyciąga dane użytkownika z id_token_claims."""
    claims = token_result.get("id_token_claims", {})

    email = (
        claims.get("email")
        or claims.get("preferred_username")
        or claims.get("upn")
        or ""
    ).lower()

    full_name = (
        claims.get("name")
        or f"{claims.get('given_name', '')} {claims.get('family_name', '')}".strip()
        or email
    )

    return {
        "email":         email,
        "full_name":     full_name,
        "external_id":   claims.get("oid") or claims.get("sub", ""),
        "tenant_id":     claims.get("tid", ""),
        "auth_provider": "microsoft",
    }
