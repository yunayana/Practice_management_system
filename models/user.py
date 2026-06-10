"""
Model użytkownika systemu.

Przechowuje dane niezależnie od dostawcy logowania (Microsoft / Google / lokalny).
Implementuje UserMixin wymagany przez Flask-Login.
"""
from datetime import datetime, timezone
from flask_login import UserMixin
from extensions import db


# ── Dostępne role ─────────────────────────────────────────────────────────────
ROLES = (
    "student",
    "opiekun_uczelniany",
    "opiekun_zakladowy",
    "pracownik_dziekanatu",
    "koordynator",
    "administrator",
)

# ── Dozwoleni dostawcy logowania ──────────────────────────────────────────────
AUTH_PROVIDERS = ("microsoft", "google", "local")


class User(UserMixin, db.Model):
    """
    Tabela użytkowników – jeden wiersz niezależnie od dostawcy logowania.

    Flask-Login wymaga is_active, is_authenticated, is_anonymous, get_id().
    UserMixin dostarcza domyślne implementacje; is_active nadpisujemy
    kolumną bazy danych.
    """

    __tablename__ = "users"

    # ── Klucz główny ─────────────────────────────────────────────────────────
    id = db.Column(db.Integer, primary_key=True)

    # ── Dane identyfikacyjne ──────────────────────────────────────────────────
    email     = db.Column(db.String(255), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(255), nullable=False)

    # ── Dane z dostawcy OAuth ─────────────────────────────────────────────────
    auth_provider = db.Column(db.String(50), nullable=False, default="microsoft")
    # oid (Microsoft) lub sub (Google) – unikalny identyfikator u dostawcy
    external_id   = db.Column(db.String(255), unique=True, nullable=True)
    # Tenant organizacji z Microsoft Entra (opcjonalny)
    tenant_id     = db.Column(db.String(255), nullable=True)

    # ── Rola i stan konta ─────────────────────────────────────────────────────
    role       = db.Column(db.String(50), nullable=False, default="student")
    # Kolumna active – nadpisuje UserMixin.is_active (UserMixin sprawdza tę właściwość)
    active     = db.Column(db.Boolean, nullable=False, default=True)

    # ── Znaczniki czasowe ─────────────────────────────────────────────────────
    created_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime, nullable=True)

    # ── Flask-Login: is_active pochodzi z kolumny 'active' ───────────────────
    @property
    def is_active(self):
        return self.active

    # ── Pomocnicze ───────────────────────────────────────────────────────────
    def has_role(self, *roles) -> bool:
        """Sprawdza, czy użytkownik ma jedną z podanych ról."""
        return self.role in roles

    def touch_login(self):
        """Aktualizuje czas ostatniego logowania."""
        self.last_login = datetime.now(timezone.utc)

    def __repr__(self):
        return f"<User {self.email} role={self.role} active={self.active}>"
