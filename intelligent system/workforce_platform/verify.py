import os
from app import create_app, init_extensions
from .extensions import db
from .models import User, Role, Employee, Skill, Task, Attendance, Team, team_members

def import_check():
    try:
        import app
        print('Import check passed')
    except Exception as e:
        print('Import check failed:', e)

def db_check(app):
    with app.app_context():
        # Ensure tables exist
        from sqlalchemy import inspect
        required_tables = {'users','roles','employees','skills','tasks','attendances','teams','team_members','employee_skills'}
        existing = set(inspect(db.engine).get_table_names())
        missing = required_tables - existing
        if missing:
            print('Missing tables:', missing)
        else:
            print('All required tables present')
        # Verify relationships via simple query
        # Create sample data
        role = Role(name='Employee')
        db.session.add(role)
        db.session.commit()
        user = User(email='test@example.com')
        user.set_password('pw')
        user.role = role
        db.session.add(user)
        db.session.commit()
        emp = Employee(user_id=user.id, first_name='Test', last_name='User')
        db.session.add(emp)
        db.session.commit()
        # skill assignment
        skill = Skill(name='Python')
        db.session.add(skill)
        db.session.commit()
        emp.skills.append(skill)
        db.session.commit()
        # Verify
        emp2 = Employee.query.filter_by(id=emp.id).first()
        if emp2.skills and emp2.skills[0].name == 'Python':
            print('Employee-skill relationship works')
        else:
            print('Employee-skill relationship failed')
        # Team membership
        team = Team(name='Alpha', department_id=1, manager_id=None, lead_id=None)
        db.session.add(team)
        db.session.commit()
        team.members.append(emp)
        db.session.commit()
        if emp in team.members:
            print('Team-members relationship works')
        else:
            print('Team-members relationship failed')

def auth_tests(app):
    # Run the test file via pytest if available, else simple
    try:
        import subprocess, sys
        result = subprocess.run([sys.executable, '-m', 'pytest', '-q', 'tests/auth_routes_test.py'], cwd='C:/Users/ELCOT/intelligent system/workforce_platform', capture_output=True, text=True)
        print('Auth tests output:')
        print(result.stdout)
        if result.returncode == 0:
            print('Authentication tests passed')
        else:
            print('Authentication tests failed')
    except Exception as e:
        print('Failed to run auth tests:', e)

if __name__ == '__main__':
    import_check()
    app = create_app()
    app.config.from_object('config.Testing')
    init_extensions(app)
    with app.app_context():
        db.drop_all()
        db.create_all()
    db_check(app)
    auth_tests(app)
