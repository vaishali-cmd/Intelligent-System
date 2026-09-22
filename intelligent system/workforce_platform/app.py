import os
from flask import Flask, redirect, url_for
from dotenv import load_dotenv
from .extensions import db, login_manager
from .config import Config

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    # Import models to ensure they are registered with SQLAlchemy metadata
    from .models import user, role, employee, department, team, skill, task, attendance
    # Note: imports are for side effects only
    

    

    # Register blueprints
    from .routes.auth import auth_bp
    from .routes.admin import admin_bp
    from .routes.manager import manager_bp
    from .routes.team_lead import lead_bp
    from .routes.employee import employee_bp
    from .routes.tasks import tasks_bp
    from .routes.leave import leave_bp

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(manager_bp, url_prefix='/manager')
    app.register_blueprint(lead_bp, url_prefix='/team-lead')
    app.register_blueprint(employee_bp, url_prefix='/employee')
    app.register_blueprint(tasks_bp, url_prefix='/tasks')
    app.register_blueprint(leave_bp)

    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    return app

# Helper to initialize extensions (db, login_manager) after app config is set.
def init_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)
    from .extensions import migrate
    migrate.init_app(app, db)
    with app.app_context():
        try:
            db.create_all()
            from .models import User
            if not User.query.first():
                from .utils.seed import seed_database
                seed_database()
        except Exception as e:
            pass

app = create_app()
init_extensions(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
