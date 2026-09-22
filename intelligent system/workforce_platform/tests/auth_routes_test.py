import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import os
from flask import Flask
from app import create_app
from workforce_platform.extensions import db
from models.role import Role
from models.user import User
from models.employee import Employee


def setup_app():
    # Use Testing config from config.py (which now includes Testing subclass)
    from config import Testing
    app = create_app()
    app.config.from_object(Testing)
    from app import init_extensions
    init_extensions(app)
    return app

app = setup_app()

with app.app_context():
    db.drop_all()
    db.create_all()
    # Create roles
    role_names = ['HR', 'Manager', 'Team Lead', 'Employee']
    roles = {}
    for name in role_names:
        r = Role(name=name)
        db.session.add(r)
        roles[name] = r
    db.session.commit()
    # Create users for each role
    users = {}
    for name in role_names:
        u = User(email=f'{name.lower()}@example.com')
        u.set_password('password123')
        u.role = roles[name]
        db.session.add(u)
        users[name] = u
    db.session.commit()
    # Create corresponding employee records (required by relationship)
    for name, user in users.items():
        emp = Employee(user_id=user.id, first_name=name, last_name='User')
        db.session.add(emp)
    db.session.commit()

    client = app.test_client()
    def login(email, password, role):
        return client.post('/auth/login', data={'email': email, 'password': password, 'role': role}, follow_redirects=False)

    # Test correct role access
    for role in role_names:
        resp = login(f'{role.lower()}@example.com', 'password123', role)
        assert resp.status_code == 302, f'Login redirect failed for {role}'
        # Follow redirect to dashboard
        dashboard_resp = client.get(resp.headers['Location'])
        assert dashboard_resp.status_code == 200, f'Correct dashboard not accessible for {role}'
        # Attempt to access wrong dashboard
        other_role = next(r for r in role_names if r != role)
        wrong_path = {
            'HR': '/admin/dashboard',
            'Manager': '/manager/dashboard',
            'Team Lead': '/team-lead/dashboard',
            'Employee': '/employee/dashboard'
        }[other_role]
        wrong_resp = client.get(wrong_path)
        assert wrong_resp.status_code == 403, f'Wrong dashboard access not blocked for {role}'
        # Logout
        client.get('/auth/logout')

    # Test not logged in access redirects
    for path in ['/admin/dashboard', '/manager/dashboard', '/team-lead/dashboard', '/employee/dashboard']:
        resp = client.get(path)
        # Should redirect to login page
        assert resp.status_code == 302 and '/auth/login' in resp.headers['Location'], f'Unauthenticated access not redirected for {path}'

print('All role-access tests passed')
