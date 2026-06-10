"""
Model studenta praktyk.
"""
from __future__ import annotations

from datetime import datetime, timezone

from extensions import db


class Student(db.Model):
    __tablename__ = "students"

    id           = db.Column(db.Integer, primary_key=True)
    first_name   = db.Column(db.String(100), nullable=False)
    last_name    = db.Column(db.String(100), nullable=False)
    index_number = db.Column(db.String(20),  unique=True, nullable=False, index=True)
    email        = db.Column(db.String(255), unique=True, nullable=False, index=True)
    # Opcjonalne powiązanie z kontem OAuth (tabela users)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at   = db.Column(db.DateTime, nullable=False,
                             default=lambda: datetime.now(timezone.utc))
    updated_at   = db.Column(db.DateTime, nullable=False,
                             default=lambda: datetime.now(timezone.utc),
                             onupdate=lambda: datetime.now(timezone.utc))

    internships = db.relationship(
        "Internship", backref="student", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "first_name":   self.first_name,
            "last_name":    self.last_name,
            "index_number": self.index_number,
            "email":        self.email,
            "user_id":      self.user_id,
            "created_at":   self.created_at.isoformat() if self.created_at else None,
            "updated_at":   self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Student {self.index_number} {self.last_name}>"
