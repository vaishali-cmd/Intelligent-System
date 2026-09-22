import os
from app import app
from .extensions import db
from models.role import Role
from models.user import User
from models.employee import Employee
from models.department import Department
from models.team import Team

# Use the globally initialized Flask app instance
flask_app = app

with flask_app.app_context():
    # Ensure DB exists (SQLAlchemy will create tables if DB exists)
    try:
        db.create_all()
        print('Tables created')
    except Exception as e:
        print('Error creating tables:', e)
        raise

    # Simple SELECT checks
    try:
        role_count = db.session.query(Role).count()
        user_count = db.session.query(User).count()
        emp_count = db.session.query(Employee).count()
        dept_count = db.session.query(Department).count()
        team_count = db.session.query(Team).count()
        print('SELECT counts:', {
            'roles': role_count,
            'users': user_count,
            'employees': emp_count,
            'departments': dept_count,
            'teams': team_count
        })
    except Exception as e:
        print('Error during SELECT queries:', e)
        raise
