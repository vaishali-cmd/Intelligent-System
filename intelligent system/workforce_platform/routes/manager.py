from flask import Blueprint, render_template
from flask_login import login_required, current_user
from ..utils.decorators import role_required
from ..models import Task, Employee, Team, Department, Attendance, TaskStatus, TaskPriority
from datetime import date

manager_bp = Blueprint('manager', __name__)

@manager_bp.route('/dashboard')
@role_required('Manager')
@login_required
def dashboard():
    emp = getattr(current_user, 'employee', None)
    dept = emp.department if emp and emp.department else None
    managed_teams = Team.query.filter_by(manager_id=emp.id).all() if emp else []
    all_teams = Team.query.all() if not managed_teams else managed_teams
    
    managed_employees = emp.managed_employees if emp and emp.managed_employees else []
    if not managed_employees:
        managed_employees = Employee.query.filter(Employee.id != (emp.id if emp else -1)).all()
        
    all_tasks = Task.query.all()
    critical_tasks = [t for t in all_tasks if t.priority == TaskPriority.CRITICAL]
    in_progress_tasks = [t for t in all_tasks if t.status == TaskStatus.IN_PROGRESS]
    completed_tasks = [t for t in all_tasks if t.status == TaskStatus.COMPLETED]
    
    today = date.today()
    attendances_today = Attendance.query.filter_by(date=today).all()

    from ..models import LeaveRequest
    leave_requests = LeaveRequest.query.order_by(LeaveRequest.id.desc()).all()

    return render_template(
        'manager/dashboard.html',
        manager=emp,
        department=dept,
        teams=all_teams,
        managed_employees=managed_employees,
        all_tasks=all_tasks,
        critical_tasks=critical_tasks,
        in_progress_tasks=in_progress_tasks,
        completed_tasks=completed_tasks,
        attendances_today=attendances_today,
        leave_requests=leave_requests,
        current_user=current_user
    )
