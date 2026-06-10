"""
Panel administratora – zarządzanie użytkownikami systemu.

Blueprint: prefix /admin

Endpointy:
  GET  /admin/users              – lista wszystkich użytkowników
  POST /admin/users/<id>/role    – zmiana roli użytkownika
  POST /admin/users/<id>/toggle  – aktywacja / dezaktywacja konta
"""
from __future__ import annotations

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from extensions import db
from models.user import User, ROLES
from utils.decorators import role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

_ADMIN_ROLES = ("administrator", "koordynator")


@admin_bp.route("/users")
@login_required
@role_required("administrator", "koordynator")
def users():
    """Lista wszystkich użytkowników z możliwością zarządzania."""
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin_users.html", users=all_users, roles=ROLES)


@admin_bp.route("/users/<int:user_id>/role", methods=["POST"])
@login_required
@role_required("administrator", "koordynator")
def change_role(user_id: int):
    """Zmień rolę użytkownika."""
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)

    # Koordynator nie może zmieniać roli administratorowi
    if user.role == "administrator" and current_user.role != "administrator":
        flash("Brak uprawnień do zmiany roli administratora.", "error")
        return redirect(url_for("admin.users"))

    new_role = request.form.get("role")
    if new_role not in ROLES:
        flash("Nieprawidłowa rola.", "error")
        return redirect(url_for("admin.users"))

    # Nie można zmienić roli samemu sobie na niższą (zabezpieczenie)
    if user.id == current_user.id and new_role not in _ADMIN_ROLES:
        flash("Nie możesz odebrać sobie uprawnień administracyjnych.", "error")
        return redirect(url_for("admin.users"))

    old_role = user.role
    user.role = new_role
    db.session.commit()
    flash(f"Rola użytkownika {user.email} zmieniona: {old_role} → {new_role}", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@role_required("administrator", "koordynator")
def toggle_active(user_id: int):
    """Aktywuj lub dezaktywuj konto użytkownika."""
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)

    if user.id == current_user.id:
        flash("Nie możesz dezaktywować własnego konta.", "error")
        return redirect(url_for("admin.users"))

    user.active = not user.active
    db.session.commit()
    status = "aktywowane" if user.active else "dezaktywowane"
    flash(f"Konto {user.email} zostało {status}.", "success")
    return redirect(url_for("admin.users"))
