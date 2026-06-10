"""
Model praktyki studenckiej.
"""
from __future__ import annotations

from datetime import datetime, timezone

from extensions import db

# Dozwolone statusy praktyki
INTERNSHIP_STATUSES = ("pending", "active", "completed", "cancelled")


class Internship(db.Model):
    __tablename__ = "internships"

    id           = db.Column(db.Integer, primary_key=True)
    student_id   = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    company_name = db.Column(db.String(255), nullable=False)
    start_date   = db.Column(db.Date, nullable=False)
    end_date     = db.Column(db.Date, nullable=False)
    status       = db.Column(db.String(50), nullable=False, default="pending")
    created_at   = db.Column(db.DateTime, nullable=False,
                             default=lambda: datetime.now(timezone.utc))
    updated_at   = db.Column(db.DateTime, nullable=False,
                             default=lambda: datetime.now(timezone.utc),
                             onupdate=lambda: datetime.now(timezone.utc))

    documents = db.relationship(
        "Document", backref="internship", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "student_id":   self.student_id,
            "company_name": self.company_name,
            "start_date":   self.start_date.isoformat() if self.start_date else None,
            "end_date":     self.end_date.isoformat()   if self.end_date   else None,
            "status":       self.status,
            "created_at":   self.created_at.isoformat() if self.created_at else None,
            "updated_at":   self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Internship {self.id} student={self.student_id} {self.company_name}>"
