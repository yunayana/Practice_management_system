"""
Zadanie 3 – API dokumentów praktyk.

Endpointy:
  GET    /api/documents                – lista dokumentów (filtr: ?internship_id=)
  POST   /api/documents                – dodaj dokument
  GET    /api/documents/<id>           – pobierz dokument
  DELETE /api/documents/<id>           – usuń dokument
  PATCH  /api/documents/<id>/verify    – aktualizuj status weryfikacji + komentarz opiekuna
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from extensions import db
from models.document import Document, DOCUMENT_TYPES, VERIFICATION_STATUSES
from models.internship import Internship
from .errors import ValidationError, NotFoundError

documents_bp = Blueprint("documents", __name__, url_prefix="/api/documents")

REQUIRED_FIELDS = ("name", "document_type", "internship_id")


def _validate_document_data(data: dict, partial: bool = False) -> None:
    """Waliduje dane dokumentu."""
    if not partial:
        missing = [f for f in REQUIRED_FIELDS if not data.get(str(f))]
        if missing:
            raise ValidationError(f"Brakujące wymagane pola: {', '.join(missing)}.")

    if "document_type" in data and data["document_type"] not in DOCUMENT_TYPES:
        raise ValidationError(
            f"Nieprawidłowy typ dokumentu '{data['document_type']}'. "
            f"Dozwolone: {', '.join(DOCUMENT_TYPES)}."
        )

    if "verification_status" in data and data["verification_status"] not in VERIFICATION_STATUSES:
        raise ValidationError(
            f"Nieprawidłowy status weryfikacji '{data['verification_status']}'. "
            f"Dozwolone: {', '.join(VERIFICATION_STATUSES)}."
        )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/documents
# ─────────────────────────────────────────────────────────────────────────────

@documents_bp.route("", methods=["GET"])
def list_documents():
    """
    Pobiera listę dokumentów.

    Parametry query (opcjonalne):
      - internship_id       – filtrowanie po ID praktyki
      - verification_status – filtrowanie po statusie weryfikacji
    """
    query = Document.query

    internship_id = request.args.get("internship_id", type=int)
    if internship_id is not None:
        if not db.session.get(Internship, internship_id):
            raise NotFoundError(f"Praktyka o ID {internship_id} nie istnieje.")
        query = query.filter_by(internship_id=internship_id)

    verification_status = request.args.get("verification_status")
    if verification_status:
        if verification_status not in VERIFICATION_STATUSES:
            raise ValidationError(
                f"Nieprawidłowy status '{verification_status}'. "
                f"Dozwolone: {', '.join(VERIFICATION_STATUSES)}."
            )
        query = query.filter_by(verification_status=verification_status)

    docs = query.order_by(Document.upload_date.desc()).all()
    return jsonify({
        "count":     len(docs),
        "documents": [d.to_dict() for d in docs],
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/documents
# ─────────────────────────────────────────────────────────────────────────────

@documents_bp.route("", methods=["POST"])
def create_document():
    """
    Dodaje nowy dokument do praktyki.

    Body JSON (wymagane):
      name, document_type, internship_id

    Body JSON (opcjonalne):
      verification_status  (domyślnie: pending)
      supervisor_comment
    """
    data = request.get_json(silent=True)
    if not data:
        raise ValidationError("Brak danych JSON w treści żądania.")

    _validate_document_data(data)

    internship_id = data.get("internship_id")
    if not isinstance(internship_id, int):
        raise ValidationError("Pole 'internship_id' musi być liczbą całkowitą.")
    if not db.session.get(Internship, internship_id):
        raise NotFoundError(f"Praktyka o ID {internship_id} nie istnieje.")

    doc = Document(
        name                = data["name"].strip(),
        document_type       = data["document_type"],
        internship_id       = internship_id,
        verification_status = data.get("verification_status", "pending"),
        supervisor_comment  = data.get("supervisor_comment"),
    )
    db.session.add(doc)
    db.session.commit()

    return jsonify(doc.to_dict()), 201


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/documents/<id>
# ─────────────────────────────────────────────────────────────────────────────

@documents_bp.route("/<int:document_id>", methods=["GET"])
def get_document(document_id: int):
    """Pobiera pojedynczy dokument po ID."""
    doc = db.session.get(Document, document_id)
    if not doc:
        raise NotFoundError(f"Dokument o ID {document_id} nie istnieje.")
    return jsonify(doc.to_dict()), 200


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/documents/<id>
# ─────────────────────────────────────────────────────────────────────────────

@documents_bp.route("/<int:document_id>", methods=["DELETE"])
def delete_document(document_id: int):
    """Usuwa dokument po ID."""
    doc = db.session.get(Document, document_id)
    if not doc:
        raise NotFoundError(f"Dokument o ID {document_id} nie istnieje.")

    db.session.delete(doc)
    db.session.commit()

    return jsonify({"message": f"Dokument ID {document_id} został usunięty."}), 200


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /api/documents/<id>/verify  (Rozszerzenie – weryfikacja przez opiekuna)
# ─────────────────────────────────────────────────────────────────────────────

@documents_bp.route("/<int:document_id>/verify", methods=["PATCH"])
def verify_document(document_id: int):
    """
    Aktualizuje status weryfikacji dokumentu i opcjonalnie dodaje komentarz opiekuna.

    Body JSON:
      verification_status  – "approved" lub "rejected"
      supervisor_comment   – (opcjonalny) komentarz opiekuna
    """
    doc = db.session.get(Document, document_id)
    if not doc:
        raise NotFoundError(f"Dokument o ID {document_id} nie istnieje.")

    data = request.get_json(silent=True)
    if not data:
        raise ValidationError("Brak danych JSON w treści żądania.")

    _validate_document_data(data, partial=True)

    if "verification_status" in data:
        doc.verification_status = data["verification_status"]
    if "supervisor_comment" in data:
        doc.supervisor_comment = data["supervisor_comment"]

    db.session.commit()
    return jsonify(doc.to_dict()), 200
