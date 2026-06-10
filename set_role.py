"""
Zmiana roli użytkownika w bazie danych.

Użycie:
    python -m flask --app app shell
    exec(open('set_role.py').read())

Lub z linii poleceń:
    python set_role.py <email> <rola>

Dostępne role:
    student, opiekun_zakladowy, opiekun_uczelniany,
    pracownik_dziekanatu, koordynator, administrator
"""
import sys

ROLES = [
    "student",
    "opiekun_zakladowy",
    "opiekun_uczelniany",
    "pracownik_dziekanatu",
    "koordynator",
    "administrator",
]


def set_role(email: str, role: str):
    from app import app
    from extensions import db
    from models.user import User

    if role not in ROLES:
        print(f"Nieprawidłowa rola: {role}")
        print(f"Dostępne role: {', '.join(ROLES)}")
        return

    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if user is None:
            print(f"Nie znaleziono użytkownika: {email}")
            return
        old_role = user.role
        user.role = role
        db.session.commit()
        print(f"OK: {email} | {old_role} → {role}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Użycie: python set_role.py <email> <rola>")
        print(f"Dostępne role: {', '.join(ROLES)}")
        sys.exit(1)
    set_role(sys.argv[1], sys.argv[2])
