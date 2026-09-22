from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, session
from flask_login import login_user, logout_user, login_required, current_user
from ..extensions import login_manager
from ..models.user import User
from ..models.role import Role

auth_bp = Blueprint('auth', __name__)

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_dashboard_route(role_name):
    mapping = {
        'HR': '/admin/dashboard',
        'Admin': '/admin/dashboard',
        'Manager': '/manager/dashboard',
        'Team Lead': '/team-lead/dashboard',
        'Employee': '/employee/dashboard'
    }
    # Fall back to employee if unknown
    return mapping.get(role_name, '/employee/dashboard')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, redirect to appropriate dashboard
    if current_user.is_authenticated:
        return redirect(get_dashboard_route(current_user.role.name))
    selected_role = session.get('selected_role')
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role_name = request.form.get('role')
        # remember choice
        session['selected_role'] = role_name
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Invalid email or password', 'error')
            return redirect(url_for('auth.login'))
        if not user.check_password(password):
            flash('Invalid email or password', 'error')
            return redirect(url_for('auth.login'))
        role_matches = (user.role.name == role_name) or (user.role.name in ('HR', 'Admin') and role_name in ('HR', 'Admin'))
        if not role_matches:
            flash(f'Selected role "{role_name}" does not match account role ({user.role.name})', 'error')
            return redirect(url_for('auth.login'))
        # Login user and remember across sessions
        login_user(user, remember=True)
        return redirect(get_dashboard_route(user.role.name))
    return render_template('auth/login.html', selected_role=selected_role)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
