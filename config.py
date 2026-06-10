"""
Konfiguracja aplikacji – wczytuje zmienne ze środowiska / pliku .env.
"""
import os
from dotenv import load_dotenv

load_dotenv()   # wczytaj plik .env z katalogu roboczego (lub nadrzędnego)


class Config:
    # ── Bezpieczeństwo ────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "zmien-na-losowy-klucz-w-produkcji")

    # ── Baza danych (SQLite domyślnie) ────────────────────────────────────────
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'praktyki.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Microsoft Entra ID / Azure AD ─────────────────────────────────────────
    MICROSOFT_CLIENT_ID     = os.environ.get("MICROSOFT_CLIENT_ID", "")
    MICROSOFT_CLIENT_SECRET = os.environ.get("MICROSOFT_CLIENT_SECRET", "")
    MICROSOFT_TENANT_ID     = os.environ.get("MICROSOFT_TENANT_ID", "common")
    MICROSOFT_REDIRECT_URI  = os.environ.get(
        "MICROSOFT_REDIRECT_URI",
        "http://localhost:5000/auth/callback/microsoft"
    )

    # Zakresy OAuth – User.Read daje dostęp do profilu + email przez Graph API
    # openid i profile są dodawane automatycznie przez MSAL
    MICROSOFT_SCOPES = ["User.Read"]

    # ── Sesja / ciasteczka ────────────────────────────────────────────────────
    # Lax: ciasteczko sesji jest wysyłane przy przekierowaniu z Microsoft (top-level GET)
    # Strict blokowałby sesję po powrocie z OAuth – NIE używać
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE   = False   # True tylko na HTTPS (produkcja)

    # ── Domeny organizacyjne ──────────────────────────────────────────────────
    # Adresy e-mail kończące się na te domeny będą traktowane jak studenci / pracownicy
    STUDENT_EMAIL_DOMAIN = os.environ.get("STUDENT_EMAIL_DOMAIN", "student.ans-elblag.pl")
    STAFF_EMAIL_DOMAIN   = os.environ.get("STAFF_EMAIL_DOMAIN",   "ans-elblag.pl")
