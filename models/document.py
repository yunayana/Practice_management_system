"""
Model dokumentu powiązanego z praktyką.
"""
from __future__ import annotations

from datetime import datetime, timezone

from extensions import db

# Dozwolone typy dokumentów
DOCUMENT_TYPES = ("confirmation", "diary", "report", "agreement", "other")

# Dozwolone statusy weryfikacji
VERIFICATION_STATUSES = ("pending", "approved", "rejected")


class Document(db.Model):
    __tablename__ = "documents"

    id                  = db.Column(db.Integer, primary_key=True)
    name                = db.Column(db.String(255), nullable=False)
    document_type       = db.Column(db.String(100), nullable=False)
    upload_date         = db.Column(db.DateTime, nullable=False,
                                    default=lambda: datetime.now(timezone.utc))
    internship_id       = db.Column(db.Integer, db.ForeignKey("internships.id"),
                                    nullable=False, index=True)
    verification_status = db.Column(db.String(50), nullable=False, default="pending")
    # Rozszerzenie: komentarz opiekuna praktyk
    supervisor_comment  = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id":                  self.id,
            "name":                self.name,
            "document_type":       self.document_type,
            "upload_date":         self.upload_date.isoformat()  if self.upload_date  else None,
            "internship_id":       self.internship_id,
            "verification_status": self.verification_status,
            "supervisor_comment":  self.supervisor_comment,
            "created_at":          self.created_at.isoformat()   if self.created_at   else None,
        }

    def __repr__(self) -> str:
        return f"<Document {self.id} '{self.name}' internship={self.internship_id}>"
