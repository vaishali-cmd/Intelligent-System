from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

# These objects will be initialised in app.create_app()

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

migrate = Migrate()
