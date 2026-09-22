from datetime import datetime, date, timedelta
from ..models.task import Task, TaskStatus, TaskPriority
from ..models.notification import Notification
from ..extensions import db

def deadline_risk(task):
    """Calculate deadline risk for a task.
    Returns a dict with keys:
        - level: 'Low', 'Medium', 'High'
        - reason: human‑readable explanation
    """
    # No due date or already completed => low risk
    if not task.due_date or task.status == TaskStatus.COMPLETED:
        return {"level": "Low", "reason": "No due date or task completed"}

    today = date.today()
    days_left = (task.due_date - today).days
    progress = getattr(task, "progress", 0) or 0
    # Base risk based on proximity
    if days_left < 0:
        base_level = "High"
        base_reason = f"Task is overdue by {-days_left} day(s)"
    elif days_left == 0:
        base_level = "High"
        base_reason = "Due today"
    elif days_left <= 2:
        base_level = "Medium"
        base_reason = f"Due in {days_left} day(s)"
    else:
        base_level = "Low"
        base_reason = f"Due in {days_left} day(s)"

    # Adjust based on progress: low progress increases risk
    if progress < 30:
        # amplify risk one step up if not already high
        if base_level == "Low":
            level = "Medium"
        elif base_level == "Medium":
            level = "High"
        else:
            level = "High"
        reason = f"Low progress ({progress}%) – {base_reason}"
    elif progress > 80:
        # high progress can mitigate risk one step down
        if base_level == "High":
            level = "Medium"
        elif base_level == "Medium":
            level = "Low"
        else:
            level = "Low"
        reason = f"High progress ({progress}%) – {base_reason}"
    else:
        level = base_level
        reason = f"Progress {progress}% – {base_reason}"

    return {"level": level, "reason": reason}

def process_deadline_risk(task, session=None):
    """Compute risk and create notification for high‑risk tasks.
    Called after task mutations. Returns risk dict.
    """
    sess = session or db.session
    risk = deadline_risk(task)
    if risk["level"] == "High":
        # Notify each assigned employee and their manager (if needed)
        for emp in task.assigned_employees:
            notif = Notification(
                recipient_id=emp.id,
                message=f"High deadline risk for task '{task.title}': {risk['reason']}"
            )
            sess.add(notif)
        # Also notify team lead (creator)
        if task.creator_id:
            notif = Notification(
                recipient_id=task.creator_id,
                message=f"High deadline risk for task '{task.title}': {risk['reason']}"
            )
            sess.add(notif)
        sess.commit()
    return risk

def is_deadline_risk(task):
    """Legacy shim returning True if risk is Medium or High (used by existing templates)."""
    return deadline_risk(task)["level"] != "Low"
