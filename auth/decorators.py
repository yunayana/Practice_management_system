"""
Dekoratory autoryzacji – używane nad funkcjami widoków Flask.

Przykład użycia:
    @app.route("/admin")
    @login_required
    @role_required("administrator")
    def panel_admina():
        ...

    @app.route("/dashboard")
    @login_required
    @role_required("student", "opiekun_uczelniany")
    def dashboard():
        ...
"""
from functools import wraps
from flask import abort
from flask_login import current_user


def role_required(*roles):
    """
    Sprawdza, czy zalogowany użytkownik ma jedną z dopuszczonych ról.

    Musi być użyty po @login_required (który gwarantuje, że current_user
    jest zalogowany). Przy braku roli – HTTP 403 Forbidden.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def active_required(fn):
    """
    Sprawdza, czy konto użytkownika zostało aktywowane (is_active=True).

    Przydatne dla kont czekających na zatwierdzenie przez administratora.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if not current_user.is_active:
            abort(403)
        return fn(*args, **kwargs)
    return wrapper
