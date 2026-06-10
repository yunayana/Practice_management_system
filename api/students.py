"""
Zadanie 1 – CRUD dla studentów praktyk.

Endpointy:
  GET    /api/students          – lista wszystkich studentów
  POST   /api/students          – dodaj studenta
  GET    /api/students/<id>     – pobierz studenta
  PUT    /api/students/<id>     – zaktualizuj studenta
  DELETE /api/students/<id>     – usuń studenta
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from extensions import db
from models.student import Student
from .errors import ValidationError, NotFoundError, ConflictError, error_response

students_bp = Blueprint("students", __name__, url_prefix="/api/students")

# Pola wymagane przy tworzeniu studenta
REQUIRED_FIELDS = ("first_name", "last_name", "index_number", "email")


def _validate_student_data(data: dict, partial: bool = False) -> None:
    """Walidacja danych studenta. partial=True przy PUT (nie wszystkie pola wymagane)."""
    if not partial:
        missing = [f for f in REQUIRED_FIELDS if not data.get(f)]
        if missing:
            raise ValidationError(
                f"Brakujące wymagane pola: {', '.join(missing)}."
            )

    email = data.get("email")
    if email is not None and "@" not in email:
        raise ValidationError("Nieprawidłowy format adresu e-mail.")


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/students
# ─────────────────────────────────────────────────────────────────────────────

@students_bp.route("", methods=["GET"])
def list_students():
    """
    Pobiera listę wszystkich studentów.

    Parametry query (opcjonalne):
      - q  – filtrowanie po nazwisku lub numerze indeksu (wyszukiwanie częściowe)
    """
    q = request.args.get("q", "").strip()
    query = Student.query

    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Student.last_name.ilike(like),
                Student.index_number.ilike(like),
                Student.email.ilike(like),
            )
        )

    students = query.order_by(Student.last_name, Student.first_name).all()
    return jsonify({
        "count": len(students),
        "students": [s.to_dict() for s in students],
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/students
# ─────────────────────────────────────────────────────────────────────────────

@students_bp.route("", methods=["POST"])
def create_student():
    """
    Tworzy nowego studenta.

    Body JSON (wymagane):
      first_name, last_name, index_number, email

    Body JSON (opcjonalne):
      user_id
    """
    data = request.get_json(silent=True)
    if not data:
        raise ValidationError("Brak danych JSON w treści żądania.")

    _validate_student_data(data)

    # Sprawdź unikalność
    if Student.query.filter_by(index_number=data["index_number"]).first():
        raise ConflictError(f"Student z numerem indeksu '{data['index_number']}' już istnieje.")
    if Student.query.filter_by(email=data["email"]).first():
        raise ConflictError(f"Student z e-mailem '{data['email']}' już istnieje.")

    student = Student(
        first_name   = data["first_name"].strip(),
        last_name    = data["last_name"].strip(),
        index_number = data["index_number"].strip(),
        email        = data["email"].strip().lower(),
        user_id      = data.get("user_id"),
    )
    db.session.add(student)
    db.session.commit()

    return jsonify(student.to_dict()), 201


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/students/<id>
# ─────────────────────────────────────────────────────────────────────────────

@students_bp.route("/<int:student_id>", methods=["GET"])
def get_student(student_id: int):
    """Pobiera pojedynczego studenta po ID."""
    student = db.session.get(Student, student_id)
    if not student:
        raise NotFoundError(f"Student o ID {student_id} nie istnieje.")
    return jsonify(student.to_dict()), 200


# ─────────────────────────────────────────────────────────────────────────────
# PUT /api/students/<id>
# ─────────────────────────────────────────────────────────────────────────────

@students_bp.route("/<int:student_id>", methods=["PUT"])
def update_student(student_id: int):
    """
    Aktualizuje dane studenta (częściowa aktualizacja – tylko podane pola).

    Body JSON (opcjonalne):
      first_name, last_name, index_number, email, user_id
    """
    student = db.session.get(Student, student_id)
    if not student:
        raise NotFoundError(f"Student o ID {student_id} nie istnieje.")

    data = request.get_json(silent=True)
    if not data:
        raise ValidationError("Brak danych JSON w treści żądania.")

    _validate_student_data(data, partial=True)

    # Sprawdź unikalność zmienianych pól
    if "index_number" in data and data["index_number"] != student.index_number:
        if Student.query.filter_by(index_number=data["index_number"]).first():
            raise ConflictError(f"Numer indeksu '{data['index_number']}' jest już zajęty.")
    if "email" in data and data["email"].lower() != student.email:
        if Student.query.filter_by(email=data["email"].lower()).first():
            raise ConflictError(f"E-mail '{data['email']}' jest już zajęty.")

    # Aktualizuj tylko podane pola
    for field in ("first_name", "last_name", "index_number", "user_id"):
        if field in data:
            setattr(student, field, data[field])
    if "email" in data:
        student.email = data["email"].strip().lower()

    db.session.commit()
    return jsonify(student.to_dict()), 200


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/students/<id>
# ─────────────────────────────────────────────────────────────────────────────

@students_bp.route("/<int:student_id>", methods=["DELETE"])
def delete_student(student_id: int):
    """
    Usuwa studenta (kaskadowo usuwa powiązane praktyki i dokumenty).
    """
    student = db.session.get(Student, student_id)
    if not student:
        raise NotFoundError(f"Student o ID {student_id} nie istnieje.")

    db.session.delete(student)
    db.session.commit()

    return jsonify({"message": f"Student ID {student_id} został usunięty."}), 200
