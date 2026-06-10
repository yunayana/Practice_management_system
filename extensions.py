"""
Singletony rozszerzeń Flask – inicjalizowane bez kontekstu aplikacji,
aby uniknąć cyklicznych importów (circular imports).
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()

login_manager = LoginManager()
login_manager.login_view = "auth.login"          # endpoint przekierowania dla @login_required
login_manager.login_message = "Zaloguj się, aby uzyskać dostęp."
login_manager.login_message_category = "warning"
