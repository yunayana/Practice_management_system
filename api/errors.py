"""
Zadanie 4 – Obsługa błędów i walidacja API.

Moduł zawiera:
  - Własne wyjątki aplikacyjne (APIError i podklasy)
  - Funkcję pomocniczą error_response()
  - Rejestrację handlerów HTTP 400 / 404 / 405 / 500 dla blueprinta API
"""
from __future__ import annotations

from flask import Blueprint, jsonify


# ─────────────────────────────────────────────────────────────────────────────
# Własne wyjątki aplikacyjne
# ─────────────────────────────────────────────────────────────────────────────

class APIError(Exception):
    """Bazowy wyjątek REST API – automatycznie zamieniany na odpowiedź JSON."""
    status_code: int = 400
    default_message: str = "Błąd żądania."

    def __init__(self, message: str | None = None, status_code: int | None = None):
        super().__init__(message or self.default_message)
        self.message = message or self.default_message
        if status_code is not None:
            self.status_code = status_code

    def to_dict(self) -> dict:
        return {"error": self.message, "status": self.status_code}


class NotFoundError(APIError):
    status_code = 404
    default_message = "Zasób nie istnieje."


class ValidationError(APIError):
    status_code = 400
    default_message = "Nieprawidłowe dane wejściowe."


class ConflictError(APIError):
    status_code = 409
    default_message = "Konflikt – zasób już istnieje."


# ─────────────────────────────────────────────────────────────────────────────
# Pomocnicza funkcja budująca odpowiedź błędu
# ─────────────────────────────────────────────────────────────────────────────

def error_response(message: str, status_code: int = 400):
    """Zwraca krotkę (Response, status_code) z JSON-ową wiadomością błędu."""
    return jsonify({"error": message, "status": status_code}), status_code


# ─────────────────────────────────────────────────────────────────────────────
# Rejestracja handlerów błędów – wywołaj register_error_handlers(app) w app.py
# ─────────────────────────────────────────────────────────────────────────────

def register_error_handlers(app) -> None:
    """Rejestruje globalne handlery błędów HTTP zwracające JSON."""

    @app.errorhandler(APIError)
    def handle_api_error(exc: APIError):
        return jsonify(exc.to_dict()), exc.status_code

    @app.errorhandler(400)
    def bad_request(exc):
        return error_response("Nieprawidłowe żądanie.", 400)

    @app.errorhandler(404)
    def not_found(exc):
        return error_response("Nie znaleziono zasobu.", 404)

    @app.errorhandler(405)
    def method_not_allowed(exc):
        return error_response("Metoda HTTP niedozwolona dla tego endpointu.", 405)

    @app.errorhandler(500)
    def internal_error(exc):
        return error_response("Wewnętrzny błąd serwera.", 500)
