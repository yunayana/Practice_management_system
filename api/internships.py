"""
Zadanie 2 – API praktyk studenckich.

Endpointy:
  GET    /api/internships                 – lista praktyk (filtr: ?student_id=)
  POST   /api/internships                 – dodaj praktykę
  GET    /api/internships/<id>            – pobierz praktykę
  PUT    /api/internships/<id>            – aktualizuj praktykę (m.in. zmiana statusu)
  DELETE /api/internships/<id>            – usuń praktykę
"""
from __future__ import annotations

from datetime import date

from flask import Blueprint, jsonify, request

from extensions import db
from models.internship import Internship, INTERNSHIP_STATUSES
from models.student import Student
from .errors import ValidationError, NotFoundError

internships_bp = Blueprint("internships", __name__, url_prefix="/api/internships")

REQUIRED_FIELDS = ("student_id", "company_name", "start_date", "end_date")


def _parse_date(value: str | None, field_name: str) -> date:
    """Parsuje datę ISO (YYYY-MM-DD); rzuca ValidationError przy błędnym formacie."""
    if not value:
        raise ValidationError(f"Pole '{field_name}' jest wymagane (format: YYYY-MM-DD).")
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValidationError(
            f"Nieprawidłowy format daty '{field_name}': '{value}'. Oczekiwano YYYY-MM-DD."
        )


def _validate_internship_data(data: dict, partial: bool = False) -> tuple[date | None, date | None]:
    """
    Waliduje dane praktyki.
    Zwraca krotkę (start_date, end_date) – None jeśli pole nie podane (partial=True).
    """
    if not partial:
        missing = [f for f in REQUIRED_FIELDS if not data.get(str(f))]
        if missing:
            raise ValidationError(f"Brakujące wymagane pola: {', '.join(missing)}.")

    start = _parse_date(data["start_date"], "start_date") if "start_date" in data else None
    end   = _parse_date(data["end_date"],   "end_date")   if "end_date"   in data else None

    if start and end and end < start:
        raise ValidationError(
            f"Data zakończenia ({data['end_date']}) nie może być wcześniejsza "
            f"niż data rozpoczęcia ({data['start_date']})."
        )

    if "status" in data and data["status"] not in INTERNSHIP_STATUSES:
        raise ValidationError(
            f"Nieprawidłowy status '{data['status']}'. "
            f"Dozwolone: {', '.join(INTERNSHIP_STATUSES)}."
        )

    return start, end


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/internships
# ─────────────────────────────────────────────────────────────────────────────

@internships_bp.route("", methods=["GET"])
def list_internships():
    """
    Pobiera listę praktyk.

    Parametry query (opcjonalne):
      - student_id  – filtrowanie po ID studenta
      - status      – filtrowanie po statusie (pending / active / completed / cancelled)
    """
    query = Internship.query

    student_id = request.args.get("student_id", type=int)
    if student_id is not None:
        # Sprawdź czy student istnieje
        if not db.session.get(Student, student_id):
            raise NotFoundError(f"Student o ID {student_id} nie istnieje.")
        query = query.filter_by(student_id=student_id)

    status = request.args.get("status")
    if status:
        if status not in INTERNSHIP_STATUSES:
            raise ValidationError(
                f"Nieprawidłowy status '{status}'. Dozwolone: {', '.join(INTERNSHIP_STATUSES)}."
            )
        query = query.filter_by(status=status)

    internships = query.order_by(Internship.start_date.desc()).all()
    return jsonify({
        "count":       len(internships),
        "internships": [i.to_dict() for i in internships],
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/internships
# ─────────────────────────────────────────────────────────────────────────────

@internships_bp.route("", methods=["POST"])
def create_internship():
    """
    Tworzy nową praktykę.

    Body JSON (wymagane):
      student_id, company_name, start_date (YYYY-MM-DD), end_date (YYYY-MM-DD)

    Body JSON (opcjonalne):
      status  (domyślnie: pending)
    """
    data = request.get_json(silent=True)
    if not data:
        raise ValidationError("Brak danych JSON w treści żądania.")

    start, end = _validate_internship_data(data)

    # Sprawdź czy student istnieje
    student_id = data.get("student_id")
    if not isinstance(student_id, int):
        raise ValidationError("Pole 'student_id' musi być liczbą całkowitą.")
    if not db.session.get(Student, student_id):
        raise NotFoundError(f"Student o ID {student_id} nie istnieje.")

    internship = Internship(
        student_id   = student_id,
        company_name = data["company_name"].strip(),
        start_date   = start,
        end_date     = end,
        status       = data.get("status", "pending"),
    )
    db.session.add(internship)
    db.session.commit()

    return jsonify(internship.to_dict()), 201


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/internships/<id>
# ─────────────────────────────────────────────────────────────────────────────

@internships_bp.route("/<int:internship_id>", methods=["GET"])
def get_internship(internship_id: int):
    """Pobiera pojedynczą praktykę po ID."""
    internship = db.session.get(Internship, internship_id)
    if not internship:
        raise NotFoundError(f"Praktyka o ID {internship_id} nie istnieje.")
    return jsonify(internship.to_dict()), 200


# ─────────────────────────────────────────────────────────────────────────────
# PUT /api/internships/<id>
# ─────────────────────────────────────────────────────────────────────────────

@internships_bp.route("/<int:internship_id>", methods=["PUT"])
def update_internship(internship_id: int):
    """
    Aktualizuje praktykę (częściowa aktualizacja – tylko podane pola).
    Typowe użycie: zmiana statusu (np. pending → active → completed).

    Body JSON (opcjonalne):
      company_name, start_date, end_date, status
    """
    internship = db.session.get(Internship, internship_id)
    if not internship:
        raise NotFoundError(f"Praktyka o ID {internship_id} nie istnieje.")

    data = request.get_json(silent=True)
    if not data:
        raise ValidationError("Brak danych JSON w treści żądania.")

    start, end = _validate_internship_data(data, partial=True)

    # Przy częściowej aktualizacji sprawdź spójność dat (łącząc z istniejącymi)
    effective_start = start or internship.start_date
    effective_end   = end   or internship.end_date
    if effective_end < effective_start:
        raise ValidationError(
            "Data zakończenia nie może być wcześniejsza niż data rozpoczęcia."
        )

    if "company_name" in data:
        internship.company_name = data["company_name"].strip()
    if start:
        internship.start_date = start
    if end:
        internship.end_date = end
    if "status" in data:
        internship.status = data["status"]

    db.session.commit()
    return jsonify(internship.to_dict()), 200


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/internships/<id>
# ─────────────────────────────────────────────────────────────────────────────

@internships_bp.route("/<int:internship_id>", methods=["DELETE"])
def delete_internship(internship_id: int):
    """Usuwa praktykę (kaskadowo usuwa powiązane dokumenty)."""
    internship = db.session.get(Internship, internship_id)
    if not internship:
        raise NotFoundError(f"Praktyka o ID {internship_id} nie istnieje.")

    db.session.delete(internship)
    db.session.commit()

    return jsonify({"message": f"Praktyka ID {internship_id} została usunięta."}), 200
