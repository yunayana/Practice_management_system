import json
import os
from flask import Flask, render_template, request, redirect, url_for

DATA_FILE = 'cv_database.json'
EFFECTS_FILE = 'effects_confirmation.json'
JOURNAL_FILE = 'practice_journal.json'

app = Flask(__name__)


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_effects():
    if os.path.exists(EFFECTS_FILE):
        with open(EFFECTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_effects(data):
    with open(EFFECTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_journals():
    if os.path.exists(JOURNAL_FILE):
        with open(JOURNAL_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_journals(data):
    with open(JOURNAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


@app.route("/")
def index():
    kandydaci = load_data()
    return render_template("edytuj_tabele.html", kandydaci=kandydaci)


@app.route("/aktualizuj-wszystko", methods=["POST"])
def aktualizuj_wszystko():
    names = request.form.getlist("fullname[]")
    emails = request.form.getlist("email[]")

    nowe_dane = [
        {"fullname": n, "email": e}
        for n, e in zip(names, emails)
        if n.strip()
    ]

    save_data(nowe_dane)
    return redirect(url_for("index"))


@app.route("/potwierdzenie", methods=["GET", "POST"])
def potwierdzenie():
    if request.method == "POST":
        effects = {}
        for i in range(1, 14):
            key = f"{i:02d}"
            effects[key] = request.form.get(f"effect_{key}") == "on"

        student = {
            "student_name": request.form.get("student_name", "").strip(),
            "album": request.form.get("album", "").strip(),
            "specialty": request.form.get("specialty", "").strip(),
            "hours": request.form.get("hours", "").strip(),
            "effects": effects,
            "company_supervisor_note": request.form.get("company_supervisor_note", "").strip(),
            "university_supervisor_opinion": request.form.get("university_supervisor_opinion", "").strip(),
        }

        students = load_effects()

        existing_index = next(
            (i for i, s in enumerate(students) if s.get("album") == student["album"]),
            None
        )

        if existing_index is not None:
            students[existing_index] = student
        else:
            students.append(student)

        save_effects(students)
        return redirect(url_for("lista_potwierdzen"))

    return render_template("potwierdzenie.html", data=None)


@app.route("/potwierdzenia")
def lista_potwierdzen():
    students = load_effects()
    return render_template("lista_potwierdzen.html", students=students)


@app.route("/potwierdzenie/<album>")
def edytuj_potwierdzenie(album):
    students = load_effects()
    student = next((s for s in students if s.get("album") == album), None)
    return render_template("potwierdzenie.html", data=student)

@app.route("/dziennik", methods=["GET", "POST"])
def dziennik():
    if request.method == "POST":
        days = request.form.getlist("day[]")
        dates = request.form.getlist("date[]")
        descriptions = request.form.getlist("description[]")
        effects_numbers = request.form.getlist("effects_numbers[]")
        supervisors = request.form.getlist("supervisor[]")

        entries = []
        for day, date, description, effect_num, supervisor in zip(
            days, dates, descriptions, effects_numbers, supervisors
        ):
            if day.strip() or date.strip() or description.strip():
                entries.append({
                    "day": day.strip(),
                    "date": date.strip(),
                    "description": description.strip(),
                    "effects_numbers": effect_num.strip(),
                    "supervisor": supervisor.strip()
                })

        student = {
            "student_name": request.form.get("student_name", "").strip(),
            "album": request.form.get("album", "").strip(),
            "specialization": request.form.get("specialization", "").strip(),
            "academic_year": request.form.get("academic_year", "").strip(),
            "practice_place": request.form.get("practice_place", "").strip(),
            "start_date": request.form.get("start_date", "").strip(),
            "end_date": request.form.get("end_date", "").strip(),
            "attachments": request.form.get("attachments", "").strip(),
            "entries": entries
        }

        journals = load_journals()

        existing_index = next(
            (i for i, s in enumerate(journals)
             if isinstance(s, dict) and s.get("album") == student["album"]),
            None
        )

        if existing_index is not None:
            journals[existing_index] = student
        else:
            journals.append(student)

        save_journals(journals)
        return redirect(url_for("lista_dziennikow"))

    return render_template("dziennik.html", data=None)

@app.route("/dzienniki")
def lista_dziennikow():
    journals = load_journals()
    return render_template("lista_dziennikow.html", journals=journals)


@app.route("/dziennik/<album>")
def edytuj_dziennik(album):
    journals = load_journals()
    student = next((s for s in journals if s.get("album") == album), None)
    return render_template("dziennik.html", data=student)