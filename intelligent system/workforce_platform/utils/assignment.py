from sqlalchemy import func
from ..models.task import Task, TaskPriority, TaskStatus
from ..models.employee import Employee
from ..models.skill import Skill
from datetime import datetime, date

def recommend_employees(task, db_session):
    """Return a list of recommendation dicts for a given task.
    Scoring is rule‑based and fully explainable.
    Each dict contains:
        - employee (Employee instance)
        - score (0‑100 int)
        - reasons (list of strings explaining points)
    """
    recommendations = []
    # Base scores
    BASE_SKILL = 40
    BASE_WORKLOAD_PENALTY = 5
    BASE_PENDING_PENALTY = 3
    PRIORITY_MULTIPLIER = {
        TaskPriority.LOW: 1.0,
        TaskPriority.MEDIUM: 1.2,
        TaskPriority.HIGH: 1.5,
        TaskPriority.CRITICAL: 2.0,
    }
    # Gather all employees
    employees = db_session.query(Employee).all()
    for emp in employees:
        score = 0
        reasons = []
        # 1. Skill match – employee must have all required skills
        emp_skill_ids = {s.id for s in emp.skills}
        required_skill_ids = {s.id for s in task.required_skills}
        if not required_skill_ids.issubset(emp_skill_ids):
            # Skip employee if missing any required skill
            continue
        else:
            score += BASE_SKILL
            reasons.append('✓ Required skills match')
        # 2. Current workload (active tasks)
        active_tasks = (
            db_session.query(Task)
            .join(Task.assigned_employees)
            .filter(Employee.id == emp.id, Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]))
            .count()
        )
        workload_penalty = active_tasks * BASE_WORKLOAD_PENALTY
        score -= workload_penalty
        reasons.append(f'⚠ {active_tasks} active tasks (‑{workload_penalty})')
        # 3. Pending tasks before this task's due date
        if task.due_date:
            pending_conflicts = (
                db_session.query(Task)
                .join(Task.assigned_employees)
                .filter(
                    Employee.id == emp.id,
                    Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
                    Task.due_date <= task.due_date,
                )
                .count()
            )
            conflict_penalty = pending_conflicts * BASE_PENDING_PENALTY
            score -= conflict_penalty
            if pending_conflicts:
                reasons.append(f'⚠ {pending_conflicts} tasks due before {task.due_date} (‑{conflict_penalty})')
        # 4. Deadline conflict – overlapping dates
        if task.start_date and task.due_date:
            overlapping = (
                db_session.query(Task)
                .join(Task.assigned_employees)
                .filter(
                    Employee.id == emp.id,
                    Task.id != task.id,
                    Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
                    Task.start_date <= task.due_date,
                    Task.due_date >= task.start_date,
                )
                .count()
            )
            if overlapping:
                score -= 10
                reasons.append(f'⚠ {overlapping} overlapping tasks (‑10)')
        # 5. Priority weighting
        multiplier = PRIORITY_MULTIPLIER.get(task.priority, 1.0)
        score = int(score * multiplier)
        reasons.append(f'✦ Priority multiplier {multiplier}')
        # Clamp score 0‑100
        score = max(0, min(100, score))
        recommendations.append({'employee': emp, 'score': score, 'reasons': reasons})
    # Sort descending by score
    recommendations.sort(key=lambda r: r['score'], reverse=True)
    return recommendations
