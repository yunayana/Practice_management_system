"""
Widoki (endpoints) modułu autoryzacji.

Blueprint: prefix /auth

Endpointy:
  GET  /auth/login                  - strona logowania (Microsoft)
  GET  /auth/login/microsoft        - start OAuth z Microsoft Entra ID
  GET  /auth/callback/microsoft     - callback po zalogowaniu w MS
  GET  /auth/logout                 - wylogowanie
  GET  /auth/pending                - konto oczekuje na zatwierdzenie
  GET  /auth/denied                 - brak dostępu (nieznana domena)
"""
from __future__ import annotations

from datetime import datetime, timezone

from flask import (
    Blueprint, current_app, flash, redirect,
    render_template_string, request, session, url_for
)
from flask_login import login_required, login_user, logout_user, current_user

from extensions import db
from models.user import User
from .microsoft import acquire_token, build_auth_url, get_user_info

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ─────────────────────────────────────────────────────────────────────────────
# Pomocnicze: ustalenie roli na podstawie domeny e-mail
# ─────────────────────────────────────────────────────────────────────────────

def _role_from_email(email: str) -> str | None:
    """
    Zwraca rolę na podstawie domeny adresu e-mail.
    Zwraca None, jeśli domena jest nieznana – dostęp odrzucony.
    """
    student_domain = current_app.config.get("STUDENT_EMAIL_DOMAIN", "student.ans.edu.pl")
    staff_domain   = current_app.config.get("STAFF_EMAIL_DOMAIN",   "ans.edu.pl")

    if email.endswith(f"@{student_domain}"):
        return "student"
    if email.endswith(f"@{staff_domain}"):
        return "opiekun_uczelniany"   # konto aktywowane ręcznie przez admina
    return None


def _handle_first_login(user_info: dict) -> User | None:
    """
    Logika pierwszego / kolejnego logowania:
      1. Szukaj użytkownika po external_id lub e-mailu.
      2. Jeśli nie istnieje – utwórz konto z rolą na podstawie domeny.
      3. Jeśli nieznana domena – zwróć None (brak dostępu).
    """
    email       = user_info["email"]
    external_id = user_info["external_id"]

    # Szukaj po external_id (oid) lub e-mailu
    user = (
        User.query.filter_by(external_id=external_id).first()
        or User.query.filter_by(email=email).first()
    )

    if user:
        # Konto istnieje – synchronizuj external_id jeśli brakuje
        if not user.external_id:
            user.external_id = external_id
        user.touch_login()
        db.session.commit()
        return user

    # Nowe konto – ustal rolę na podstawie domeny e-mail
    role = _role_from_email(email)
    if role is None:
        current_app.logger.warning("Odmowa dostępu dla domeny: %s", email)
        return None

    # Studenci aktywni od razu; pracownicy czekają na zatwierdzenie
    is_active = (role == "student")

    user = User(
        email         = email,
        full_name     = user_info.get("full_name", email),
        auth_provider = "microsoft",
        external_id   = external_id,
        tenant_id     = user_info.get("tenant_id"),
        role          = role,
        active        = is_active,
        last_login    = datetime.now(timezone.utc),
    )
    db.session.add(user)
    db.session.commit()
    current_app.logger.info(
        "Nowe konto: %s (rola: %s, aktywne: %s)", email, role, is_active
    )
    return user


# ─────────────────────────────────────────────────────────────────────────────
# Widoki
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/login")
def login():
    """Strona logowania przez Microsoft."""
    if current_user.is_authenticated:
        # Użytkownik już zalogowany – idź do aplikacji
        return redirect(_safe_next() or url_for("dashboard"))

    html = """
    <!DOCTYPE html><html lang="pl"><head><meta charset="UTF-8">
    <title>Logowanie – Praktyki</title>
    <style>
      * { box-sizing: border-box; margin: 0; padding: 0; }
      body { font-family: Arial, sans-serif; display: flex; justify-content: center;
             align-items: center; height: 100vh; background: #f0f4f8; }
      .card { background: #fff; padding: 48px 40px; border-radius: 12px;
              box-shadow: 0 4px 20px rgba(0,0,0,0.12); text-align: center; min-width: 340px; }
      h1 { color: #1F3864; margin-bottom: 6px; font-size: 22px; }
      p  { color: #666; margin-bottom: 32px; font-size: 14px; }
      .btn { display: flex; align-items: center; justify-content: center; gap: 10px;
             width: 100%; padding: 13px; border: none; border-radius: 6px;
             font-size: 15px; cursor: pointer; text-decoration: none; }
      .btn-ms { background: #0078d4; color: #fff; }
      .btn-ms:hover { background: #006cbf; }
      .flash { margin-bottom: 16px; padding: 10px 14px; border-radius: 6px;
               font-size: 13px; background: #fee2e2; color: #c00; }
    </style></head><body>
    <div class="card">
      <h1>System obsługi praktyk</h1>
      <p>Zaloguj się kontem organizacyjnym uczelni</p>
      {% for msg in get_flashed_messages() %}
        <div class="flash">{{ msg }}</div>
      {% endfor %}
      <a class="btn btn-ms" href="{{ ms_url }}">
        <svg width="18" height="18" viewBox="0 0 21 21" xmlns="http://www.w3.org/2000/svg">
          <rect x="1" y="1" width="9" height="9" fill="#f25022"/>
          <rect x="11" y="1" width="9" height="9" fill="#7fba00"/>
          <rect x="1" y="11" width="9" height="9" fill="#00a4ef"/>
          <rect x="11" y="11" width="9" height="9" fill="#ffb900"/>
        </svg>
        Zaloguj przez Microsoft
      </a>
    </div></body></html>
    """
    # Zachowaj parametr ?next= w sesji, żeby po callback móc wrócić
    next_url = request.args.get("next")
    if next_url:
        session["login_next"] = next_url

    from flask import get_flashed_messages
    return render_template_string(html,
        ms_url=url_for("auth.login_microsoft"),
        get_flashed_messages=get_flashed_messages,
    )


def _safe_next() -> str | None:
    """
    Bezpieczne odczytanie docelowego URL po zalogowaniu.
    Bierze z sesji (zapisane przez stronę /auth/login) lub query param.
    Akceptuje tylko ścieżki wewnętrzne (zaczyna się od /).
    """
    next_url = session.pop("login_next", None) or request.args.get("next")
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return None


# ── Microsoft ─────────────────────────────────────────────────────────────────

@auth_bp.route("/login/microsoft")
def login_microsoft():
    """Przekierowuje do strony logowania Microsoft Entra ID."""
    return redirect(build_auth_url())


@auth_bp.route("/callback/microsoft")
def callback_microsoft():
    """
    Callback OAuth po zalogowaniu w Microsoft.

    1. Sprawdź parametry error / code.
    2. Wymień kod na token (MSAL) – weryfikacja state CSRF.
    3. Wyciągnij dane użytkownika z id_token_claims.
    4. Utwórz / zaktualizuj konto (logika pierwszego logowania).
    5. Zaloguj przez Flask-Login i przekieruj do aplikacji.
    """
    if "error" in request.args:
        flash(
            f"Błąd logowania Microsoft: "
            f"{request.args.get('error_description', request.args.get('error'))}",
            "danger"
        )
        return redirect(url_for("auth.login"))

    code  = request.args.get("code")
    state = request.args.get("state")

    if not code:
        flash("Brakujący kod autoryzacyjny.", "danger")
        return redirect(url_for("auth.login"))

    # Wymiana kodu na token (zwraca krotkę: wynik, błąd)
    token_result, token_error = acquire_token(code, state)
    if token_result is None:
        flash(token_error or "Nie udało się uzyskać tokena.", "danger")
        return redirect(url_for("auth.login"))

    user_info = get_user_info(token_result)
    if not user_info.get("email"):
        flash("Nie można odczytać adresu e-mail z konta Microsoft.", "danger")
        return redirect(url_for("auth.login"))

    user = _handle_first_login(user_info)

    if user is None:
        return redirect(url_for("auth.denied"))

    if not user.is_active:
        return redirect(url_for("auth.pending"))

    # Zaloguj użytkownika – Flask-Login ustawia sesję
    success = login_user(user, remember=True)
    if not success:
        flash("Logowanie nie powiodło się – konto może być nieaktywne.", "danger")
        return redirect(url_for("auth.login"))

    # Przekieruj do strony, którą użytkownik chciał odwiedzić, lub do dashboardu
    next_url = _safe_next()
    return redirect(next_url or url_for("dashboard"))


# ── Wylogowanie ───────────────────────────────────────────────────────────────

@auth_bp.route("/logout")
@login_required
def logout():
    """Wylogowanie: czyści sesję Flask-Login i sesję OAuth."""
    session.clear()
    logout_user()
    flash("Zostałeś wylogowany.", "info")
    return redirect(url_for("auth.login"))


# ── Strony informacyjne ───────────────────────────────────────────────────────

@auth_bp.route("/pending")
def pending():
    """Konto pracownicze oczekujące na zatwierdzenie przez administratora."""
    html = """
    <!DOCTYPE html><html lang="pl"><head><meta charset="UTF-8"><title>Konto oczekuje</title>
    <style>body{font-family:Arial;display:flex;justify-content:center;align-items:center;
    height:100vh;background:#f2f2f2;margin:0;}
    .box{text-align:center;padding:40px;background:#fff;border-radius:6px;
    box-shadow:0 2px 12px rgba(0,0,0,.08);max-width:420px;border:1px solid #d1d5db;}
    h2{color:#374151;margin-bottom:16px;} p{color:#6b7280;margin-bottom:12px;font-size:14px;}
    a{color:#374151;text-decoration:underline;}</style></head>
    <body><div class="box">
      <h2>Konto oczekuje na aktywację</h2>
      <p>Twoje konto pracownicze zostało zarejestrowane i czeka na zatwierdzenie
      przez administratora systemu.</p>
      <p>Skontaktuj się z dziekanatem lub
      <a href="mailto:admin@ans.edu.pl">napisz do admina</a>.</p>
      <p><a href="{{ url }}">&#x2190; Powrót do logowania</a></p>
    </div></body></html>
    """
    return render_template_string(html, url=url_for("auth.login"))


@auth_bp.route("/denied")
def denied():
    """Odmowa dostępu – nierozpoznana domena e-mail."""
    student_domain = current_app.config.get("STUDENT_EMAIL_DOMAIN", "student.ans.edu.pl")
    staff_domain   = current_app.config.get("STAFF_EMAIL_DOMAIN",   "ans.edu.pl")
    html = """
    <!DOCTYPE html><html lang="pl"><head><meta charset="UTF-8"><title>Brak dostępu</title>
    <style>body{font-family:Arial;display:flex;justify-content:center;align-items:center;
    height:100vh;background:#f2f2f2;margin:0;}
    .box{text-align:center;padding:40px;background:#fff;border-radius:6px;
    box-shadow:0 2px 12px rgba(0,0,0,.08);max-width:420px;border:1px solid #d1d5db;}
    h2{color:#374151;margin-bottom:16px;} p{color:#6b7280;margin-bottom:12px;font-size:14px;}
    em{font-style:normal;font-weight:bold;} a{color:#374151;text-decoration:underline;}</style></head>
    <body><div class="box">
      <h2>Brak dostępu</h2>
      <p>Twój adres e-mail nie należy do żadnej z obsługiwanych domen organizacyjnych.</p>
      <p>Dostęp mają tylko konta:<br>
         <em>@{{ student_domain }}</em> (studenci)<br>
         <em>@{{ staff_domain }}</em> (pracownicy – po zatwierdzeniu)</p>
      <p><a href="{{ url }}">&#x2190; Powrót do logowania</a></p>
    </div></body></html>
    """
    return render_template_string(html,
        student_domain=student_domain,
        staff_domain=staff_domain,
        url=url_for("auth.login"),
    )
