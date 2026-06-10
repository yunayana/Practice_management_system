"""
Główny moduł aplikacji Flask – obsługa praktyk zawodowych.

Struktura:
  extensions.py        – singletony db, login_manager
  config.py            – konfiguracja z .env
  models/              – modele SQLAlchemy (User, Student, Internship, Document)
  auth/                – logowanie OAuth 2.0 (Microsoft Entra ID), role, sesje
  api/                 – REST API (students, internships, documents, errors)
"""
from __future__ import annotations

import io
import json
import os
import zipfile

from flask import Flask, render_template, render_template_string, request, redirect, url_for, send_from_directory, send_file
from flask_login import login_required, current_user

from pdf_generator import (
    generate_confirmation_pdf, generate_journal_pdf, generate_report_pdf,
    generate_card_pdf, generate_survey_pdf, generate_report7_pdf,
)

from config import Config
from extensions import db, login_manager
from models.user import User
from auth.routes import auth_bp
from api.students import students_bp
from api.internships import internships_bp
from api.documents import documents_bp
from api.errors import register_error_handlers
from admin.routes import admin_bp


# ─────────────────────────────────────────────────────────────────────────────
# Fabryka aplikacji
# ─────────────────────────────────────────────────────────────────────────────

def create_app(config_class=Config) -> Flask:
    """
    Tworzy i konfiguruje instancję Flask (application factory pattern).
    user_loader musi być zarejestrowany PO init_app – dlatego jest tutaj,
    nie na poziomie modułu.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ── Rozszerzenia ──────────────────────────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)

    # ── Flask-Login: callback ładowania użytkownika z bazy ────────────────────
    # Musi być wewnątrz create_app, PO init_app, żeby login_manager
    # był już związany z aplikacją.
    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        try:
            return db.session.get(User, int(user_id))
        except (ValueError, Exception):
            return None

    # ── Blueprinty ────────────────────────────────────────────────────────────
    app.register_blueprint(auth_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(internships_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(admin_bp)

    # ── Ujednolicona obsługa błędów API ───────────────────────────────────────
    register_error_handlers(app)

    # ── Tworzenie tabel przy starcie (SQLite – dev) ───────────────────────────
    with app.app_context():
        # Import wszystkich modeli zapewnia, że tabele zostaną utworzone
        import models  # noqa: F401
        db.create_all()

    return app


# ─────────────────────────────────────────────────────────────────────────────
# Pliki JSON (legacy – utrzymane dla kompatybilności wstecznej)
# ─────────────────────────────────────────────────────────────────────────────

EFFECTS_FILE = "effects_confirmation.json"
JOURNAL_FILE = "practice_journal.json"
KARTA_FILE   = "practice_cards.json"
SURVEY_FILE  = "practice_surveys.json"
REPORT7_FILE = "practice_reports.json"


def _load(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


load_effects  = lambda: _load(EFFECTS_FILE)
save_effects  = lambda d: _save(EFFECTS_FILE, d)
load_journals = lambda: _load(JOURNAL_FILE)
save_journals = lambda d: _save(JOURNAL_FILE, d)
load_cards    = lambda: _load(KARTA_FILE)
save_cards    = lambda d: _save(KARTA_FILE, d)
load_surveys  = lambda: _load(SURVEY_FILE)
save_surveys  = lambda d: _save(SURVEY_FILE, d)
load_reports7 = lambda: _load(REPORT7_FILE)
save_reports7 = lambda d: _save(REPORT7_FILE, d)


# ─────────────────────────────────────────────────────────────────────────────
# Instancja aplikacji
# ─────────────────────────────────────────────────────────────────────────────

app = create_app()


# ─────────────────────────────────────────────────────────────────────────────
# Widoki
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    return redirect(url_for("dashboard"))


def _student_album(user) -> str:
    """Zwraca numer albumu studenta na podstawie prefiksu adresu e-mail."""
    return user.email.split("@")[0]


def _is_student() -> bool:
    return current_user.is_authenticated and current_user.role == "student"


def _check_student_album(album: str) -> bool:
    """True jeśli student próbuje dostać się do cudzego albumu."""
    return _is_student() and _student_album(current_user) != album


def _viewer_role() -> str:
    """Zwraca rolę aktualnie zalogowanego użytkownika (do widoków)."""
    return current_user.role if current_user.is_authenticated else ""


@app.route("/dashboard")
@login_required
def dashboard():
    """Spersonalizowany pulpit – strona po zalogowaniu."""
    role = current_user.role

    # ── Student ───────────────────────────────────────────────────────────────
    if role == "student":
        album = _student_album(current_user)
        filled = {
            "karta":         any(c.get("album") == album for c in load_cards()),
            "potwierdzenie": any(s.get("album") == album for s in load_effects()),
            "ankieta":       any(s.get("album") == album for s in load_surveys()),
            "dziennik":      any(j.get("album") == album for j in load_journals()),
            "sprawozdanie":  any(r.get("album") == album for r in load_reports7()),
        }
        return render_template("dashboard_student.html",
                               user=current_user, album=album, filled=filled)

    # ── Opiekun zakładowy ────────────────────────────────────────────────────
    if role == "opiekun_zakladowy":
        return render_template(
            "dashboard_opiekun_zakladowy.html",
            user=current_user,
            cards=load_cards(),
            effects=load_effects(),
        )

    # ── Opiekun uczelniany ───────────────────────────────────────────────────
    if role == "opiekun_uczelniany":
        all_effects = load_effects()
        pending   = [s for s in all_effects if not s.get("university_supervisor_opinion")]
        completed = [s for s in all_effects if s.get("university_supervisor_opinion")]
        stats = {
            "karty":         len(load_cards()),
            "potwierdzenia": len(all_effects),
            "dzienniki":     len(load_journals()),
            "sprawozdania":  len(load_reports7()),
        }
        return render_template(
            "dashboard_opiekun_uczelniany.html",
            user=current_user,
            stats=stats,
            pending_opinions=pending,
            completed_opinions=completed,
            opinions_missing=len(pending),
        )

    # ── Koordynator ───────────────────────────────────────────────────────────
    if role == "koordynator":
        cards     = load_cards()
        effects   = load_effects()
        surveys   = load_surveys()
        journals  = load_journals()
        reports   = load_reports7()
        # Zbierz unikalne albumy
        albums = {}
        for c in cards:
            a = c.get("album")
            if a:
                albums.setdefault(a, {"album": a, "student_name": c.get("student_name", "")})
        for s in effects:
            a = s.get("album")
            if a:
                albums.setdefault(a, {"album": a, "student_name": s.get("student_name", "")})
        # Buduj tabelę kompletności
        completion = []
        for a, info in sorted(albums.items()):
            completion.append({
                "album":             a,
                "student_name":      info["student_name"],
                "has_karta":         any(c.get("album") == a for c in cards),
                "has_potwierdzenie": any(s.get("album") == a for s in effects),
                "has_ankieta":       any(s.get("album") == a for s in surveys),
                "has_dziennik":      any(j.get("album") == a for j in journals),
                "has_sprawozdanie":  any(r.get("album") == a for r in reports),
            })
        stats = {
            "karty":         len(cards),
            "potwierdzenia": len(effects),
            "ankiety":       len(surveys),
            "dzienniki":     len(journals),
            "sprawozdania":  len(reports),
        }
        return render_template(
            "dashboard_koordynator.html",
            user=current_user,
            stats=stats,
            completion=completion,
        )

    # ── Pozostałe role (pracownik_dziekanatu, administrator) ──────────────────
    stats = {
        "karty":         len(load_cards()),
        "potwierdzenia": len(load_effects()),
        "ankiety":       len(load_surveys()),
        "dzienniki":     len(load_journals()),
        "sprawozdania":  len(load_reports7()),
    }
    return render_template("dashboard_staff.html", user=current_user, stats=stats)


_POTWIERDZENIE_SUPERVISOR_FIELDS = [
    "student_name", "album", "specialty", "hours",
    "company_supervisor_note",
]
_POTWIERDZENIE_UCZELNIANY_FIELDS = ["university_supervisor_opinion"]


@app.route("/potwierdzenie", methods=["GET", "POST"])
@login_required
def potwierdzenie():
    role = _viewer_role()
    if _is_student() and request.method == "GET":
        return redirect(url_for("edytuj_potwierdzenie", album=_student_album(current_user)))
    if request.method == "POST":
        album = _student_album(current_user) if _is_student() else request.form.get("album", "").strip()

        # Merge-save: wczytaj istniejący rekord, nadpisz tylko pola tej roli
        all_effects = load_effects()
        idx = next((i for i, s in enumerate(all_effects) if s.get("album") == album), None)
        existing = all_effects[idx] if idx is not None else {}
        merged = dict(existing)
        merged["album"] = album

        if role == "opiekun_uczelniany":
            # Opiekun uczelniany nadpisuje tylko swoją opinię
            merged["university_supervisor_opinion"] = request.form.get(
                "university_supervisor_opinion", "").strip()
        else:
            # Opiekun zakładowy / personel nadpisuje dane studenta i efekty
            for f in _POTWIERDZENIE_SUPERVISOR_FIELDS:
                merged[f] = request.form.get(f, "").strip()
            merged["effects"] = {
                f"{i:02d}": request.form.get(f"effect_{i:02d}") == "on"
                for i in range(1, 14)
            }
            if role not in ("opiekun_zakladowy",):
                # Pełen personel może też nadpisać opinię uczelnianą
                merged["university_supervisor_opinion"] = request.form.get(
                    "university_supervisor_opinion", "").strip()

        if idx is not None:
            all_effects[idx] = merged
        else:
            all_effects.append(merged)
        save_effects(all_effects)
        return redirect(url_for("lista_potwierdzen"))
    return render_template("potwierdzenie.html", data=None, locked_album=None,
                           viewer_role=role)


@app.route("/potwierdzenia")
@login_required
def lista_potwierdzen():
    data = load_effects()
    if _is_student():
        album = _student_album(current_user)
        data = [s for s in data if s.get("album") == album]
    return render_template("lista_potwierdzen.html", students=data)


@app.route("/potwierdzenie/<album>")
@login_required
def edytuj_potwierdzenie(album):
    if _check_student_album(album):
        return redirect(url_for("edytuj_potwierdzenie", album=_student_album(current_user)))
    student = next((s for s in load_effects() if s.get("album") == album), None)
    locked = _student_album(current_user) if _is_student() else None
    if student is None and _is_student():
        student = {"album": album}
    role = _viewer_role()
    return render_template("potwierdzenie.html", data=student, locked_album=locked,
                           viewer_role=role)


@app.route("/dziennik", methods=["GET", "POST"])
@login_required
def dziennik():
    if _is_student() and request.method == "GET":
        return redirect(url_for("edytuj_dziennik", album=_student_album(current_user)))
    if request.method == "POST":
        album = _student_album(current_user) if _is_student() else request.form.get("album", "").strip()
        days         = request.form.getlist("day[]")
        dates        = request.form.getlist("date[]")
        descriptions = request.form.getlist("description[]")
        effects_numbers = request.form.getlist("effects_numbers[]")
        supervisors  = request.form.getlist("supervisor[]")

        entries = [
            {
                "day":             day.strip(),
                "date":            date.strip(),
                "description":     desc.strip(),
                "effects_numbers": eff.strip(),
                "supervisor":      sup.strip(),
            }
            for day, date, desc, eff, sup in zip(
                days, dates, descriptions, effects_numbers, supervisors
            )
            if any([day.strip(), date.strip(), desc.strip()])
        ]
        student = {
            "student_name":   request.form.get("student_name", "").strip(),
            "album":          album,
            "specialization": request.form.get("specialization", "").strip(),
            "academic_year":  request.form.get("academic_year", "").strip(),
            "practice_place": request.form.get("practice_place", "").strip(),
            "start_date":     request.form.get("start_date", "").strip(),
            "end_date":       request.form.get("end_date", "").strip(),
            "attachments":    request.form.get("attachments", "").strip(),
            "entries":        entries,
        }
        journals = load_journals()
        idx = next(
            (i for i, s in enumerate(journals)
             if isinstance(s, dict) and s.get("album") == student["album"]),
            None
        )
        if idx is not None:
            journals[idx] = student
        else:
            journals.append(student)
        save_journals(journals)
        return redirect(url_for("lista_dziennikow"))
    return render_template("dziennik.html", data=None, locked_album=None)


@app.route("/dzienniki")
@login_required
def lista_dziennikow():
    data = load_journals()
    if _is_student():
        album = _student_album(current_user)
        data = [j for j in data if isinstance(j, dict) and j.get("album") == album]
    return render_template("lista_dziennikow.html", journals=data)


@app.route("/dziennik/<album>")
@login_required
def edytuj_dziennik(album):
    if _check_student_album(album):
        return redirect(url_for("edytuj_dziennik", album=_student_album(current_user)))
    student = next((s for s in load_journals() if s.get("album") == album), None)
    locked = _student_album(current_user) if _is_student() else None
    if student is None and _is_student():
        student = {"album": album}
    return render_template("dziennik.html", data=student, locked_album=locked)


# ─────────────────────────────────────────────────────────────────────────────
# Swagger UI
# ─────────────────────────────────────────────────────────────────────────────

_SWAGGER_HTML = """<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="UTF-8">
  <title>API – System praktyk</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.17.14/swagger-ui.min.css">
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.17.14/swagger-ui-bundle.min.js"></script>
<script>
  SwaggerUIBundle({
    url: "/static/swagger.yaml",
    dom_id: "#swagger-ui",
    presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
    layout: "BaseLayout",
    deepLinking: true,
  });
</script>
</body>
</html>"""


@app.route("/api/docs")
def api_docs():
    """Interaktywna dokumentacja REST API (Swagger UI)."""
    return render_template_string(_SWAGGER_HTML)


@app.route("/api/test")
@login_required
def api_test():
    """Panel do ręcznego testowania endpointów REST API (Zadanie 3)."""
    return render_template("api_test.html")


# ─────────────────────────────────────────────────────────────────────────────
# Etap 11 – Generowanie PDF
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/kalendarz/<album>")
@login_required
def kalendarz(album):
    """Widok kalendarza z dniami wpisanymi w dzienniku praktyki."""
    if _check_student_album(album):
        return redirect(url_for("kalendarz", album=_student_album(current_user)))
    journal = next((j for j in load_journals() if isinstance(j, dict) and j.get("album") == album), None)
    entries = journal.get("entries", []) if journal else []
    # Filtruj tylko wpisy z datą
    entries = [e for e in entries if e.get("date")]
    return render_template(
        "kalendarz.html",
        album=album,
        entries=entries,
        entries_json=json.dumps(entries, ensure_ascii=False),
    )


@app.route("/generate-pdf/potwierdzenie/<album>")
@login_required
def pdf_potwierdzenie(album: str):
    """Pobierz potwierdzenie efektów uczenia się jako PDF."""
    students = load_effects()
    data = next((s for s in students if s.get("album") == album), None)
    if data is None:
        return f"Nie znaleziono potwierdzenia dla albumu: {album}", 404

    buf = generate_confirmation_pdf(data)
    filename = f"potwierdzenie_{album}.pdf"
    return send_file(buf, mimetype="application/pdf",
                     download_name=filename, as_attachment=True)


@app.route("/generate-pdf/dziennik/<album>")
@login_required
def pdf_dziennik(album: str):
    """Pobierz dziennik praktyki jako PDF."""
    journals = load_journals()
    data = next((j for j in journals if isinstance(j, dict) and j.get("album") == album), None)
    if data is None:
        return f"Nie znaleziono dziennika dla albumu: {album}", 404

    buf = generate_journal_pdf(data)
    filename = f"dziennik_{album}.pdf"
    return send_file(buf, mimetype="application/pdf",
                     download_name=filename, as_attachment=True)


@app.route("/generate-pdf/raport/<album>")
@login_required
def pdf_raport(album: str):
    """Pobierz raport końcowy (oba dokumenty) jako PDF."""
    students  = load_effects()
    journals  = load_journals()

    conf_data = next((s for s in students if s.get("album") == album), None)
    jour_data = next(
        (j for j in journals if isinstance(j, dict) and j.get("album") == album), None
    )

    if conf_data is None and jour_data is None:
        return f"Nie znaleziono żadnych danych dla albumu: {album}", 404

    buf = generate_report_pdf(conf_data, jour_data)
    filename = f"raport_praktyki_{album}.pdf"
    return send_file(buf, mimetype="application/pdf",
                     download_name=filename, as_attachment=True)


# ── Zadanie 8: Zbiorczy eksport ZIP ──────────────────────────────────────────

@app.route("/generate-pdf/zip/<album>")
@login_required
def pdf_zip_student(album: str):
    """
    Pobierz archiwum ZIP ze wszystkimi dokumentami jednego studenta:
      - potwierdzenie_<album>.pdf
      - dziennik_<album>.pdf
      - raport_praktyki_<album>.pdf
    """
    students  = load_effects()
    journals  = load_journals()

    conf_data = next((s for s in students if s.get("album") == album), None)
    jour_data = next(
        (j for j in journals if isinstance(j, dict) and j.get("album") == album), None
    )

    if conf_data is None and jour_data is None:
        return f"Nie znaleziono żadnych danych dla albumu: {album}", 404

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if conf_data:
            buf = generate_confirmation_pdf(conf_data)
            zf.writestr(f"potwierdzenie_{album}.pdf", buf.read())
        if jour_data:
            buf = generate_journal_pdf(jour_data)
            zf.writestr(f"dziennik_{album}.pdf", buf.read())
        # Raport końcowy zawsze (jeśli jest choć jeden dokument)
        buf = generate_report_pdf(conf_data, jour_data)
        zf.writestr(f"raport_praktyki_{album}.pdf", buf.read())

    zip_buf.seek(0)
    return send_file(zip_buf, mimetype="application/zip",
                     download_name=f"dokumenty_praktyki_{album}.zip",
                     as_attachment=True)


@app.route("/generate-pdf/zip-all")
@login_required
def pdf_zip_all():
    """
    Pobierz archiwum ZIP z raportami końcowymi wszystkich studentów.
    Struktura: raport_praktyki_<album>.pdf dla każdego albumu.
    """
    students = load_effects()
    journals = load_journals()

    if not students and not journals:
        return "Brak danych do wyeksportowania.", 404

    # Zbierz unikalne numery albumów
    albums = set()
    for s in students:
        if s.get("album"):
            albums.add(s["album"])
    for j in journals:
        if isinstance(j, dict) and j.get("album"):
            albums.add(j["album"])

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for album in sorted(albums):
            conf = next((s for s in students if s.get("album") == album), None)
            jour = next((j for j in journals if isinstance(j, dict) and j.get("album") == album), None)
            buf = generate_report_pdf(conf, jour)
            zf.writestr(f"raport_praktyki_{album}.pdf", buf.read())

    zip_buf.seek(0)
    return send_file(zip_buf, mimetype="application/zip",
                     download_name="wszystkie_raporty.zip",
                     as_attachment=True)


# ─────────────────────────────────────────────────────────────────────────────
# Zał. nr 3 – Karta praktyki zawodowej
# ─────────────────────────────────────────────────────────────────────────────

_KARTA_STUDENT_FIELDS = [
    "student_name", "album", "study_program", "specialization",
    "academic_year", "semester", "university_supervisor",
    "start_date", "end_date", "total_hours",
]
_KARTA_COMPANY_FIELDS = [
    "company_name", "company_address", "company_phone", "company_nip",
    "company_type", "company_supervisor_name", "company_supervisor_title",
    "grade", "company_supervisor_opinion",
]


@app.route("/karta", methods=["GET", "POST"])
@login_required
def karta():
    role = _viewer_role()
    if _is_student() and request.method == "GET":
        return redirect(url_for("edytuj_karte", album=_student_album(current_user)))
    if request.method == "POST":
        album = _student_album(current_user) if _is_student() else request.form.get("album", "").strip()

        # Merge-save: wczytaj istniejący rekord, nadpisz tylko pola tej roli
        all_cards = load_cards()
        idx = next((i for i, c in enumerate(all_cards) if c.get("album") == album), None)
        existing = all_cards[idx] if idx is not None else {}
        merged = dict(existing)
        merged["album"] = album

        if role == "student":
            fields = _KARTA_STUDENT_FIELDS
        elif role == "opiekun_zakladowy":
            fields = _KARTA_COMPANY_FIELDS
        else:
            fields = _KARTA_STUDENT_FIELDS + _KARTA_COMPANY_FIELDS

        for f in fields:
            if f != "album":
                merged[f] = request.form.get(f, "").strip()

        if idx is not None:
            all_cards[idx] = merged
        else:
            all_cards.append(merged)
        save_cards(all_cards)
        return redirect(url_for("lista_kart"))
    return render_template("karta.html", data=None, locked_album=None, viewer_role=role)


@app.route("/karty")
@login_required
def lista_kart():
    data = load_cards()
    if _is_student():
        album = _student_album(current_user)
        data = [c for c in data if c.get("album") == album]
    return render_template("lista_kart.html", cards=data)


@app.route("/karta/<album>")
@login_required
def edytuj_karte(album):
    if _check_student_album(album):
        return redirect(url_for("edytuj_karte", album=_student_album(current_user)))
    card = next((c for c in load_cards() if c.get("album") == album), None)
    locked = _student_album(current_user) if _is_student() else None
    if card is None and _is_student():
        card = {"album": album}
    role = _viewer_role()
    return render_template("karta.html", data=card, locked_album=locked, viewer_role=role)


@app.route("/generate-pdf/karta/<album>")
@login_required
def pdf_karta(album: str):
    """Pobierz kartę praktyki jako PDF (Załącznik nr 3)."""
    data = next((c for c in load_cards() if c.get("album") == album), None)
    if data is None:
        return f"Nie znaleziono karty dla albumu: {album}", 404
    buf = generate_card_pdf(data)
    return send_file(buf, mimetype="application/pdf",
                     download_name=f"karta_praktyki_{album}.pdf", as_attachment=True)


# ─────────────────────────────────────────────────────────────────────────────
# Zał. nr 5 – Kwestionariusz ankiety
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/kwestionariusz", methods=["GET", "POST"])
@login_required
def kwestionariusz():
    if _is_student() and request.method == "GET":
        return redirect(url_for("edytuj_ankiete", album=_student_album(current_user)))
    if request.method == "POST":
        album = _student_album(current_user) if _is_student() else request.form.get("album", "").strip()
        survey = {
            "student_name":  request.form.get("student_name", "").strip(),
            "album":         album,
            "academic_year": request.form.get("academic_year", "").strip(),
            "company_name":  request.form.get("company_name", "").strip(),
            "most_valuable": request.form.get("most_valuable", "").strip(),
            "improvements":  request.form.get("improvements", "").strip(),
            "recommend":     request.form.get("recommend", "").strip(),
            "comments":      request.form.get("comments", "").strip(),
        }
        for q in [f"q{i}" for i in range(1, 11)]:
            survey[q] = request.form.get(q, "").strip()
        surveys = load_surveys()
        idx = next((i for i, s in enumerate(surveys) if s.get("album") == survey["album"]), None)
        if idx is not None:
            surveys[idx] = survey
        else:
            surveys.append(survey)
        save_surveys(surveys)
        return redirect(url_for("lista_ankiet"))
    return render_template("kwestionariusz.html", data=None, locked_album=None)


@app.route("/ankiety")
@login_required
def lista_ankiet():
    data = load_surveys()
    if _is_student():
        album = _student_album(current_user)
        data = [s for s in data if s.get("album") == album]
    return render_template("lista_ankiet.html", surveys=data)


@app.route("/kwestionariusz/<album>")
@login_required
def edytuj_ankiete(album):
    if _check_student_album(album):
        return redirect(url_for("edytuj_ankiete", album=_student_album(current_user)))
    survey = next((s for s in load_surveys() if s.get("album") == album), None)
    locked = _student_album(current_user) if _is_student() else None
    if survey is None and _is_student():
        survey = {"album": album}
    return render_template("kwestionariusz.html", data=survey, locked_album=locked)


@app.route("/generate-pdf/ankieta/<album>")
@login_required
def pdf_ankieta(album: str):
    """Pobierz kwestionariusz ankiety jako PDF (Załącznik nr 5)."""
    data = next((s for s in load_surveys() if s.get("album") == album), None)
    if data is None:
        return f"Nie znaleziono ankiety dla albumu: {album}", 404
    buf = generate_survey_pdf(data)
    return send_file(buf, mimetype="application/pdf",
                     download_name=f"ankieta_{album}.pdf", as_attachment=True)


# ─────────────────────────────────────────────────────────────────────────────
# Zał. nr 7 – Sprawozdanie z praktyki zawodowej
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/sprawozdanie", methods=["GET", "POST"])
@login_required
def sprawozdanie():
    if _is_student() and request.method == "GET":
        return redirect(url_for("edytuj_sprawozdanie", album=_student_album(current_user)))
    if request.method == "POST":
        album_val = _student_album(current_user) if _is_student() else request.form.get("album", "").strip()
        self_effects = {
            f"{i:02d}": request.form.get(f"self_effect_{i:02d}") == "on"
            for i in range(1, 14)
        }
        report = {
            "student_name":        request.form.get("student_name", "").strip(),
            "album":               album_val,
            "specialization":      request.form.get("specialization", "").strip(),
            "academic_year":       request.form.get("academic_year", "").strip(),
            "company_name":        request.form.get("company_name", "").strip(),
            "company_address":     request.form.get("company_address", "").strip(),
            "start_date":          request.form.get("start_date", "").strip(),
            "end_date":            request.form.get("end_date", "").strip(),
            "company_description": request.form.get("company_description", "").strip(),
            "department":          request.form.get("department", "").strip(),
            "tasks_description":   request.form.get("tasks_description", "").strip(),
            "technologies":        request.form.get("technologies", "").strip(),
            "projects":            request.form.get("projects", "").strip(),
            "problems":            request.form.get("problems", "").strip(),
            "conclusions":         request.form.get("conclusions", "").strip(),
            "self_effects":        self_effects,
        }
        reports = load_reports7()
        idx = next((i for i, r in enumerate(reports) if r.get("album") == report["album"]), None)
        if idx is not None:
            reports[idx] = report
        else:
            reports.append(report)
        save_reports7(reports)
        return redirect(url_for("lista_sprawozdan"))
    return render_template("sprawozdanie.html", data=None, locked_album=None)


@app.route("/sprawozdania")
@login_required
def lista_sprawozdan():
    data = load_reports7()
    if _is_student():
        album = _student_album(current_user)
        data = [r for r in data if r.get("album") == album]
    return render_template("lista_sprawozdan.html", reports=data)


@app.route("/sprawozdanie/<album>")
@login_required
def edytuj_sprawozdanie(album):
    if _check_student_album(album):
        return redirect(url_for("edytuj_sprawozdanie", album=_student_album(current_user)))
    report = next((r for r in load_reports7() if r.get("album") == album), None)
    locked = _student_album(current_user) if _is_student() else None
    if report is None and _is_student():
        report = {"album": album}
    return render_template("sprawozdanie.html", data=report, locked_album=locked)


@app.route("/generate-pdf/sprawozdanie/<album>")
@login_required
def pdf_sprawozdanie(album: str):
    """Pobierz sprawozdanie z praktyki jako PDF (Załącznik nr 7)."""
    data = next((r for r in load_reports7() if r.get("album") == album), None)
    if data is None:
        return f"Nie znaleziono sprawozdania dla albumu: {album}", 404
    buf = generate_report7_pdf(data)
    return send_file(buf, mimetype="application/pdf",
                     download_name=f"sprawozdanie_{album}.pdf", as_attachment=True)


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
