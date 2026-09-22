from functools import wraps
from flask import abort, redirect, url_for, flash
from flask_login import current_user, login_required

def role_required(*role_names):
    """Decorator that ensures the logged‑in user has one of the specified roles.
    If the user does not have the role, return 403 Forbidden.
    """
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            user_role = getattr(current_user, 'role', None)
            allowed_roles = set(role_names)
            if 'HR' in allowed_roles:
                allowed_roles.add('Admin')
            if 'Admin' in allowed_roles:
                allowed_roles.add('HR')
            if not user_role or user_role.name not in allowed_roles:
                flash('You do not have permission to access this page.', 'error')
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator
