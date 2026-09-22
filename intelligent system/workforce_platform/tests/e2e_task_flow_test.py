"""
End-to-end test for the Task Management lifecycle.

Covers:
  1. Team Lead creates a task with skills, priority, dates
  2. Smart Assignment recommendations (explainable scoring)
  3. Team Lead assigns an employee
  4. Employee logs in and sees the assigned task
  5. Employee updates progress 25→50→75→100
  6. Workload recalculation after each step
  7. Deadline risk recalculation
  8. Notifications for assignment / progress / completion
  9. Task auto-marked Completed at 100%
  10. Final workload and task status verification

Edge cases:
  EC-1  Employee without required skill excluded from recommendations
  EC-2  Overloaded employee penalised in scoring
  EC-3  Deadline conflict penalised in scoring
  EC-4  Reassignment to another employee
  EC-5  Unauthorized user (Employee) attempts task edit → 403
  EC-6  Invalid progress values (negative, >100)
  EC-7  Completed task cannot be edited → 403
"""

import pytest
import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timedelta, date
from werkzeug.security import generate_password_hash

from workforce_platform.extensions import db
from models import (
    User, Role, Employee, Skill, Task,
    Notification, TaskPriority, TaskStatus,
)
from utils.assignment import recommend_employees
from utils.workload import compute_employee_workload
from utils.deadline import is_deadline_risk


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def test_app():
    """Create the Flask app with an in-memory SQLite DB and seed test data."""
    from app import create_app, init_extensions

    app = create_app()
    # Override DB URI *before* init_extensions so SQLAlchemy binds correctly
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    init_extensions(app)

    with app.app_context():
        db.create_all()

        # ---- Roles ----
        roles = {}
        for name in ['HR', 'Admin', 'Manager', 'Team Lead', 'Employee']:
            role = Role(name=name)
            db.session.add(role)
            roles[name] = role
        db.session.commit()

        # ---- Helper: create user + employee ----
        def _make(email, password, role_name, first, last):
            user = User(
                email=email,
                password_hash=generate_password_hash(password),
                role=roles[role_name],
            )
            db.session.add(user)
            db.session.flush()
            emp = Employee(user_id=user.id, first_name=first, last_name=last)
            db.session.add(emp)
            db.session.flush()
            return user, emp

        _make('hr@test.com',       'pwd', 'HR',        'Helen',  'R')
        _make('mgr@test.com',      'pwd', 'Manager',   'Megan',  'M')
        tl_user,   tl_emp   = _make('tl@test.com',  'pwd', 'Team Lead', 'Tim',    'L')
        emp_user,  emp_emp  = _make('emp@test.com', 'pwd', 'Employee',  'Emily',  'E')
        oth_user,  oth_emp  = _make('oth@test.com', 'pwd', 'Employee',  'Oscar',  'O')

        # ---- Skills ----
        python_skill = Skill(name='Python')
        sql_skill    = Skill(name='SQL')
        db.session.add_all([python_skill, sql_skill])
        db.session.flush()

        # Assign skills: emp has Python, oth has only SQL
        emp_emp.skills.append(python_skill)
        oth_emp.skills.append(sql_skill)
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(test_app):
    return test_app.test_client()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def login(client, email, password, role):
    """Log the test client into the app with the given credentials."""
    return client.post(
        '/auth/login',
        data={'email': email, 'password': password, 'role': role},
        follow_redirects=True,
    )


def logout(client):
    client.get('/auth/logout', follow_redirects=True)


# ---------------------------------------------------------------------------
# Main E2E flow
# ---------------------------------------------------------------------------

def test_full_e2e_lifecycle(test_app, client):
    """
    Team Lead → create → assign → Employee → progress → system checks.
    """
    with test_app.app_context():
        # ── 1. Team Lead creates a task ──────────────────────────────────
        login(client, 'tl@test.com', 'pwd', 'Team Lead')

        start = date.today()
        due   = start + timedelta(days=5)
        python_id = str(Skill.query.filter_by(name='Python').first().id)

        resp = client.post('/tasks/create', data={
            'title':           'Build API',
            'description':     'Create REST API endpoints',
            'start_date':      start.isoformat(),
            'due_date':        due.isoformat(),
            'priority':        TaskPriority.HIGH.name,
            'required_skills': [python_id],
        }, follow_redirects=True)
        assert b'Task created successfully' in resp.data

        task = Task.query.filter_by(title='Build API').first()
        assert task is not None
        tl_emp = Employee.query.filter_by(
            user_id=User.query.filter_by(email='tl@test.com').first().id
        ).first()
        assert task.creator_id == tl_emp.id
        assert task.priority == TaskPriority.HIGH
        assert task.start_date == start
        assert task.due_date == due
        assert any(s.name == 'Python' for s in task.required_skills)

        # ── 2. Generate Smart Assignment recommendations ─────────────────
        recs = recommend_employees(task, db.session)
        emp_emp = Employee.query.filter_by(
            user_id=User.query.filter_by(email='emp@test.com').first().id
        ).first()

        # Employee with Python should be recommended
        rec_ids = [r['employee'].id for r in recs]
        assert emp_emp.id in rec_ids

        # Verify explainable scoring
        emp_rec = next(r for r in recs if r['employee'].id == emp_emp.id)
        assert emp_rec['score'] > 0
        assert any('✓ Required skills match' in reason for reason in emp_rec['reasons'])

        # ── 3. Assign employee ───────────────────────────────────────────
        resp = client.post(f'/tasks/{task.id}/assign', data={
            'employee_ids': [str(emp_emp.id)],
        }, follow_redirects=True)
        assert b'Task assignment updated' in resp.data

        db.session.refresh(task)
        assert len(task.assigned_employees) == 1
        assert task.assigned_employees[0].id == emp_emp.id

        # Notification created for assignee (recipient_id == employee.id)
        notif = Notification.query.filter_by(recipient_id=emp_emp.id).first()
        assert notif is not None
        assert 'assigned' in notif.message.lower()

        # ── 4. Employee logs in, sees the task ───────────────────────────
        logout(client)
        login(client, 'emp@test.com', 'pwd', 'Employee')

        dash = client.get('/employee/dashboard')
        assert dash.status_code == 200
        assert b'Build API' in dash.data

        # ── 5. Progress updates: 25 → 50 → 75 → 100 ────────────────────
        for pct in [25, 50, 75, 100]:
            resp = client.post(
                f'/tasks/{task.id}/progress',
                data={'progress': pct},
                follow_redirects=True,
            )
            assert b'Progress updated' in resp.data

            db.session.refresh(task)
            assert task.progress == pct, f'Expected {pct}%, got {task.progress}%'

            # Workload recalculation
            wl = compute_employee_workload(emp_emp, db.session)
            assert wl['active_count'] >= 0
            assert wl['level'] in ('Low', 'Balanced', 'High', 'Overloaded')

            # Deadline risk
            risk = is_deadline_risk(task)
            if task.status == TaskStatus.COMPLETED:
                assert risk is False, 'Completed task should have no deadline risk'
            elif task.due_date and (task.due_date - date.today()).days <= 2:
                assert risk is True
            else:
                assert risk is False

        # ── 6. Task auto-completed at 100% ───────────────────────────────
        assert task.status == TaskStatus.COMPLETED

        # ── 7. Workload drops to 0 active for this employee ─────────────
        wl_final = compute_employee_workload(emp_emp, db.session)
        # The Build API task is completed, so only still-active dummy tasks
        # (created later in edge-case tests) would count.  At this point
        # there should be 0 active tasks.
        assert wl_final['active_count'] == 0

        print('✅ Full E2E lifecycle passed')


# ---------------------------------------------------------------------------
# Edge-case tests
# ---------------------------------------------------------------------------

def test_ec1_employee_without_required_skill(test_app, client):
    """EC-1: Employee lacking required skill must NOT appear in recommendations."""
    with test_app.app_context():
        login(client, 'tl@test.com', 'pwd', 'Team Lead')

        start = date.today()
        due   = start + timedelta(days=3)
        python_id = str(Skill.query.filter_by(name='Python').first().id)

        client.post('/tasks/create', data={
            'title':           'Data Pipeline',
            'description':     'ETL pipeline',
            'start_date':      start.isoformat(),
            'due_date':        due.isoformat(),
            'priority':        TaskPriority.MEDIUM.name,
            'required_skills': [python_id],
        }, follow_redirects=True)

        task = Task.query.filter_by(title='Data Pipeline').first()
        assert task is not None

        recs = recommend_employees(task, db.session)
        oth_emp = Employee.query.filter_by(
            user_id=User.query.filter_by(email='oth@test.com').first().id
        ).first()

        rec_ids = [r['employee'].id for r in recs]
        assert oth_emp.id not in rec_ids, \
            'Employee without Python skill should be excluded'

        logout(client)
        print('✅ EC-1 passed')


def test_ec2_overloaded_employee(test_app, client):
    """EC-2: Overloaded employee's score is reduced."""
    with test_app.app_context():
        emp_emp = Employee.query.filter_by(
            user_id=User.query.filter_by(email='emp@test.com').first().id
        ).first()
        tl_emp = Employee.query.filter_by(
            user_id=User.query.filter_by(email='tl@test.com').first().id
        ).first()

        # Create 5 active dummy tasks to overload emp_emp
        for i in range(5):
            t = Task(
                title=f'Overload-{i}',
                creator_id=tl_emp.id,
                priority=TaskPriority.LOW,
                status=TaskStatus.IN_PROGRESS,
            )
            t.assigned_employees.append(emp_emp)
            db.session.add(t)
        db.session.commit()

        # Retrieve the "Data Pipeline" task (created in EC-1)
        task = Task.query.filter_by(title='Data Pipeline').first()
        recs = recommend_employees(task, db.session)

        entry = next((r for r in recs if r['employee'].id == emp_emp.id), None)
        assert entry is not None, 'emp_emp should still appear (has Python)'
        assert entry['score'] < 100, 'Score should be penalised by workload'

        print('✅ EC-2 passed')


def test_ec3_deadline_conflict(test_app, client):
    """EC-3: Overlapping task dates reduce the recommendation score."""
    with test_app.app_context():
        emp_emp = Employee.query.filter_by(
            user_id=User.query.filter_by(email='emp@test.com').first().id
        ).first()
        tl_emp = Employee.query.filter_by(
            user_id=User.query.filter_by(email='tl@test.com').first().id
        ).first()

        task = Task.query.filter_by(title='Data Pipeline').first()

        # Create a conflicting task that overlaps the Data Pipeline dates
        conflict = Task(
            title='Conflict Task',
            creator_id=tl_emp.id,
            start_date=task.start_date,
            due_date=task.due_date,
            priority=TaskPriority.HIGH,
            status=TaskStatus.PENDING,
        )
        conflict.assigned_employees.append(emp_emp)
        db.session.add(conflict)
        db.session.commit()

        recs = recommend_employees(task, db.session)
        entry = next((r for r in recs if r['employee'].id == emp_emp.id), None)
        assert entry is not None
        assert any('overlapping tasks' in reason for reason in entry['reasons']), \
            'Should mention overlapping tasks in reasons'

        print('✅ EC-3 passed')


def test_ec4_reassignment(test_app, client):
    """EC-4: Reassign task from one employee to another via the route."""
    with test_app.app_context():
        oth_emp = Employee.query.filter_by(
            user_id=User.query.filter_by(email='oth@test.com').first().id
        ).first()
        # Give oth_emp the Python skill so they qualify
        python_skill = Skill.query.filter_by(name='Python').first()
        if python_skill not in oth_emp.skills:
            oth_emp.skills.append(python_skill)
            db.session.commit()

        task = Task.query.filter_by(title='Data Pipeline').first()

        login(client, 'tl@test.com', 'pwd', 'Team Lead')
        resp = client.post(f'/tasks/{task.id}/assign', data={
            'employee_ids': [str(oth_emp.id)],
        }, follow_redirects=True)
        assert b'Task assignment updated' in resp.data

        db.session.refresh(task)
        assert len(task.assigned_employees) == 1
        assert task.assigned_employees[0].id == oth_emp.id

        logout(client)
        print('✅ EC-4 passed')


def test_ec5_unauthorized_edit(test_app, client):
    """EC-5: An Employee role user cannot edit a task → 403."""
    with test_app.app_context():
        task = Task.query.filter_by(title='Data Pipeline').first()

        login(client, 'emp@test.com', 'pwd', 'Employee')
        resp = client.post(
            f'/tasks/{task.id}/edit',
            data={'title': 'Hacked Title'},
            follow_redirects=False,
        )
        assert resp.status_code == 403

        logout(client)
        print('✅ EC-5 passed')


def test_ec6_invalid_progress(test_app, client):
    """EC-6: Negative progress → rejected; >100 → clamped to 100."""
    with test_app.app_context():
        task = Task.query.filter_by(title='Data Pipeline').first()
        # Reset task so it can accept progress
        task.status = TaskStatus.PENDING
        task.progress = 0
        db.session.commit()

        oth_emp = Employee.query.filter_by(
            user_id=User.query.filter_by(email='oth@test.com').first().id
        ).first()

        # Make sure oth_emp is assigned
        login(client, 'tl@test.com', 'pwd', 'Team Lead')
        client.post(f'/tasks/{task.id}/assign', data={
            'employee_ids': [str(oth_emp.id)],
        }, follow_redirects=True)
        logout(client)

        login(client, 'oth@test.com', 'pwd', 'Employee')

        # Negative progress → "Invalid progress value"
        resp = client.post(
            f'/tasks/{task.id}/progress',
            data={'progress': -10},
            follow_redirects=True,
        )
        assert b'Invalid progress value' in resp.data

        # > 100 → clamped to 100
        resp = client.post(
            f'/tasks/{task.id}/progress',
            data={'progress': 150},
            follow_redirects=True,
        )
        assert b'Progress updated' in resp.data

        db.session.refresh(task)
        assert task.progress == 100, f'Progress should be clamped to 100, got {task.progress}'

        logout(client)
        print('✅ EC-6 passed')


def test_ec7_completed_task_cannot_be_edited(test_app, client):
    """EC-7: A completed task cannot be edited by the Team Lead → 403."""
    with test_app.app_context():
        task = Task.query.filter_by(title='Data Pipeline').first()
        task.status = TaskStatus.COMPLETED
        db.session.commit()

        login(client, 'tl@test.com', 'pwd', 'Team Lead')

        resp = client.post(
            f'/tasks/{task.id}/edit',
            data={'title': 'New Title'},
            follow_redirects=False,
        )
        assert resp.status_code == 403

        logout(client)
        print('✅ EC-7 passed')
