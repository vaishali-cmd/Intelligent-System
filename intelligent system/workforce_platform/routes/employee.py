from flask import Blueprint, render_template
from flask_login import login_required, current_user
from ..utils.decorators import role_required
from ..models import Task, Employee, Attendance
from datetime import date

employee_bp = Blueprint('employee', __name__)

@employee_bp.route('/dashboard')
@role_required('Employee')
@login_required
def dashboard():
    emp = getattr(current_user, 'employee', None)
    if not emp:
        return render_template('employee/dashboard.html', tasks=[], employee=None, attendance=None, current_user=current_user)
        
    tasks = Task.query.join(Task.assigned_employees).filter(Employee.id == emp.id).all()
    if not tasks:
        # Fallback to all tasks if none explicitly assigned yet
        tasks = Task.query.limit(4).all()
        
    today = date.today()
    attendance = Attendance.query.filter_by(employee_id=emp.id, date=today).first()

    from ..models import LeaveRequest
    my_leaves = LeaveRequest.query.filter_by(employee_id=emp.id).order_by(LeaveRequest.id.desc()).all()
    
    return render_template(
        'employee/dashboard.html',
        tasks=tasks,
        employee=emp,
        attendance=attendance,
        my_leaves=my_leaves,
        today=today,
        current_user=current_user
    )
