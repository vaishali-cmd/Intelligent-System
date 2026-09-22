from datetime import datetime
from ..models.task import Task, TaskPriority, TaskStatus
from ..models.employee import Employee
from ..extensions import db

from datetime import datetime
from ..models.task import Task, TaskPriority, TaskStatus
from ..models.employee import Employee
from ..models.workload import Workload
from ..extensions import db


def calculate_workload(emp, session=None):
    """Calculate workload for an employee.

    Returns a dict with:
        - percent (0-100)
        - total_weight (weighted units)
        - level (Low/Balanced/High/Overloaded)
        - active_count
        - factors (list of strings explaining each task's contribution)
    """
    sess = session or db.session
    # Active tasks are Pending, In Progress, or Blocked (half weight)
    active_tasks = (
        sess.query(Task)
        .join(Task.assigned_employees)
        .filter(
            Employee.id == emp.id,
            Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED])
        )
        .all()
    )
    active_count = len(active_tasks)
    priority_factor = {
        TaskPriority.LOW: 1.0,
        TaskPriority.MEDIUM: 1.2,
        TaskPriority.HIGH: 1.5,
        TaskPriority.CRITICAL: 2.0,
    }
    total_weight = 0.0
    factors = []
    for t in active_tasks:
        base = priority_factor.get(t.priority, 1.0)
        progress_factor = 1 + (100 - t.progress) / 100.0
        weight = base * progress_factor
        if t.status == TaskStatus.BLOCKED:
            weight *= 0.5  # half weight for blocked tasks
        total_weight += weight
        factors.append(
            f"Task {t.id}: priority={t.priority.name}, progress={t.progress}%, status={t.status.name}, weight={round(weight,2)}"
        )
    # Capacity: 8 weighted units = 100%
    percent = min(100, (total_weight / 8) * 100)
    if percent < 30:
        level = 'Low'
    elif percent < 60:
        level = 'Balanced'
    elif percent < 90:
        level = 'High'
    else:
        level = 'Overloaded'
    return {
        'percent': round(percent, 2),
        'total_weight': round(total_weight, 2),
        'level': level,
        'active_count': active_count,
        'factors': factors,
    }


def update_employee_workload(emp, session=None):
    """Compute workload and upsert the Workload model for the given employee.
    Lazily creates the record if it does not exist.
    """
    sess = session or db.session
    result = calculate_workload(emp, sess)
    workload = sess.query(Workload).filter_by(employee_id=emp.id).first()
    if not workload:
        workload = Workload(employee_id=emp.id)
        sess.add(workload)
    workload.total_hours = result['total_weight']
    workload.status = result['level']
    workload.last_calculated = datetime.utcnow()
    sess.commit()
    return result


def compute_employee_workload(emp, db_session=None):
    """Legacy wrapper kept for backward compatibility – returns the calculation dict without DB side‑effects."""
    return calculate_workload(emp, db_session)
