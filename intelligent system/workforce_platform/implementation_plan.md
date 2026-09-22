# Task Management & Intelligence Implementation

**Goal**: Add full task management capabilities, smart assignment, workload intelligence, deadline risk detection, and notifications while maintaining the existing authentication and database foundation.

## User Review Required
> **[!IMPORTANT]** No open questions remain – the user has approved the overall direction. Ensure all new code respects the existing Flask‑Login role system and does not introduce any ML/AI components.

## Proposed Changes
---
### Models & Relationships
- **`models/task.py`** already extended with priority, status, dates, progress, remarks, `required_skills` (via `task_skills` table) and `assigned_employees` (via existing `task_assignments`).
- Ensure imports of `Enum` and enum classes are present.
- Add **`utils/assignment.py`**: rule‑based recommendation engine.
- Add **`utils/workload.py`**: workload calculation and imbalance detection.
- Add **`utils/deadline.py`**: deadline‑risk detection helper.
- Add **`models/notification.py`** (simple model with `recipient_id`, `message`, `created_at`).

---
### Routes (new blueprint `routes/tasks.py`)
- `GET /tasks` – TL view of tasks they own.
- `GET /tasks/create` + `POST /tasks/create` – create task form.
- `GET /tasks/<int:id>` – detail view (any logged‑in user can view their assigned tasks; TL/Manager can view all).
- `GET /tasks/<int:id>/edit` + `POST /tasks/<int:id>/edit` – edit task (TL owner or Manager).
- `POST /tasks/<int:id>/assign` – assign/reassign employees (TL).
- `POST /tasks/<int:id>/status` – update status/progress.
- `GET /manager/tasks` – manager overview of all tasks.
- All routes protected with `@login_required` and `@role_required` where appropriate.

---
### Templates
- `templates/tasks/list.html` – card/grid view of tasks with filters.
- `templates/tasks/detail.html` – shows all fields, required skills, assigned employees, progress bar, remarks, and recommendation panel.
- `templates/tasks/form.html` – create/edit form with dropdowns for priority/status, date pickers, multi‑select skills, progress slider.
- UI follows premium design (gradient headers, glass‑morphism cards, responsive layout).

---
### Smart Assignment Utility (`utils/assignment.py`)
```python
def recommend_employees(task, db_session):
    """Return a list of (employee, score, reasons) tuples.
    Scoring rules (explainable):
    1. Skill match – 40 points if employee has *all* required skills.
    2. Current workload – subtract 5 points per active task.
    3. Pending tasks before due date – subtract 3 points per conflict.
    4. Priority weighting – multiply base score by 1.0 for Low, 1.2 for Medium, 1.5 for High, 2.0 for Critical.
    5. Deadline conflict – -10 points if any assigned task overlaps the new task's dates.
    The final score is capped at 100 and expressed as a percentage.
    """
    # Implementation uses real DB queries; no ML.
```
- Returns sorted list; UI displays check‑marks (✓) and warnings (⚠).

---
### Workload Calculation (`utils/workload.py`)
```python
def compute_employee_workload(emp):
    active = db.session.query(Task).join(task_assignments)
        .filter(task_assignments.c.employee_id == emp.id,
                Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]))
        .all()
    weight = sum({TaskPriority.LOW:1, TaskPriority.MEDIUM:1.2,
                  TaskPriority.HIGH:1.5, TaskPriority.CRITICAL:2}[t.priority] * (t.progress/100 + 1) for t in active)
    percent = min(100, (weight / 8) * 100)  # assume 8‑task capacity
    if percent < 30: level='Low'
    elif percent < 60: level='Balanced'
    elif percent < 90: level='High'
    else: level='Overloaded'
    return {'percent': percent, 'active_count': len(active), 'level': level}
```
- Team‑level aggregation builds distribution for manager dashboard.

---
### Deadline‑Risk Detection (`utils/deadline.py`)
```python
def is_deadline_risk(task):
    # Returns True if due date is within 2 days and status not Completed.
    if not task.due_date: return False
    days_left = (task.due_date - datetime.utcnow().date()).days
    return days_left <= 2 and task.status != TaskStatus.COMPLETED
```
- Flag shown on task detail and manager overview.

---
### Notifications (`models/notification.py` & helper `utils/notify.py`)
- Simple model: `id, recipient_id (FK User), message, created_at`.
- Helper `create_notification(user, message)` inserts a row.
- When a task is assigned/reassigned, generate notifications for old and new assignees.

---
### Tests (`tests/task_flow_test.py`)
1. Setup roles, users, employees, skills.
2. TL logs in, creates a task with required skills.
3. Call `recommend_employees` and assert at least one candidate returned with expected reasons.
4. Assign task via POST `/tasks/<id>/assign`.
5. Employee fetches `/tasks/<id>` – verify assignment present.
6. TL updates progress → workload recalculated; assert workload level changes.
7. Simulate near‑due date → `is_deadline_risk` returns True.
8. Complete task → status changes, workload drops, notification generated.
9. All assertions pass; test exits with code 0.

---
## Verification Plan
### Automated Tests
- Run `pytest -q tests/task_flow_test.py` after migrations.
### Manual Verification Steps
1. Start the app (`flask run`).
2. Login as Team Lead, create task, observe recommendation panel.
3. Assign task, logout, login as Employee, verify task appears.
4. Update progress, check workload badge on employee dashboard.
5. Verify deadline‑risk badge appears when due date is close.
6. Complete task, ensure workload badge returns to Low/Balanced.
7. Check `notifications` table for correct messages.

Once all checks pass, proceed to **Leave Management + Leave Impact Analysis**.
