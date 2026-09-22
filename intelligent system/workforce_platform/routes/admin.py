from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import date
from ..extensions import db
from ..utils.decorators import role_required
from ..models import User, Employee, Department, Role, Task, Attendance, Skill, LeaveRequest

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
@role_required('HR', 'Admin')
@login_required
def dashboard():
    users = User.query.all()
    employees = Employee.query.order_by(Employee.id.desc()).all()
    departments = Department.query.all()
    roles = Role.query.all()
    skills = Skill.query.all()
    leave_requests = LeaveRequest.query.order_by(LeaveRequest.id.desc()).all()
    tasks_count = Task.query.count()
    active_employees_count = Employee.query.filter_by(status='active').count()
    
    return render_template(
        'admin/dashboard.html',
        users=users,
        employees=employees,
        departments=departments,
        roles=roles,
        skills=skills,
        leave_requests=leave_requests,
        tasks_count=tasks_count,
        active_employees_count=active_employees_count,
        current_user=current_user
    )

@admin_bp.route('/employee/create', methods=['POST'])
@role_required('HR', 'Admin')
@login_required
def create_employee():
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip() or 'Workforce2026!'
    role_name = request.form.get('role_name', 'Employee')
    dept_id = request.form.get('department_id')
    phone = request.form.get('phone', '').strip()
    skill_ids = request.form.getlist('skills')

    if not first_name or not last_name or not email:
        flash('First Name, Last Name, and Email are required.', 'error')
        return redirect(url_for('admin.dashboard'))

    # Check if user already exists
    if User.query.filter_by(email=email).first():
        flash(f'An account with email "{email}" already exists.', 'error')
        return redirect(url_for('admin.dashboard'))

    # Find role
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        role = Role.query.filter_by(name='Employee').first()

    # Create User
    new_user = User(
        email=email,
        password_hash=generate_password_hash(password),
        role=role
    )
    db.session.add(new_user)
    db.session.flush()

    # Create Employee
    new_emp = Employee(
        user_id=new_user.id,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        department_id=int(dept_id) if dept_id else None,
        joining_date=date.today(),
        status='active'
    )
    db.session.add(new_emp)
    db.session.flush()

    # Attach skills
    if skill_ids:
        selected_skills = Skill.query.filter(Skill.id.in_(skill_ids)).all()
        new_emp.skills.extend(selected_skills)

    db.session.commit()
    flash(f'Employee {new_emp.full_name} ({email}) created successfully as {role_name}!', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/employee/<int:emp_id>/delete', methods=['POST'])
@role_required('HR', 'Admin')
@login_required
def delete_employee(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    name = emp.full_name
    user = emp.user

    # Prevent deleting own account
    if user and user.id == current_user.id:
        flash('You cannot delete your own logged-in account!', 'error')
        return redirect(url_for('admin.dashboard'))

    db.session.delete(emp)
    if user:
        db.session.delete(user)
    db.session.commit()
    flash(f'Employee {name} removed successfully.', 'info')
    return redirect(url_for('admin.dashboard'))
