from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user
from ..extensions import db
from ..models import Task, TaskStatus, Employee, Skill, Notification
from ..utils.assignment import recommend_employees
from ..utils.workload import compute_employee_workload, update_employee_workload
from ..utils.deadline import is_deadline_risk, process_deadline_risk
from ..utils.decorators import role_required
from datetime import datetime

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')

# Helper to check if current user can access a task (owner TL or Manager)
def _can_access_task(task):
    if current_user.role.name == 'Manager':
        return True
    # Team Lead can access tasks they created (owner stored via creator_id)
    return getattr(task, 'creator_id', None) == current_user.employee.id
@tasks_bp.route('/')
@login_required
@role_required('Team Lead')
def list_tasks():
    employee = current_user.employee
    tasks = Task.query.join(Task.assigned_employees).filter(Employee.id == employee.id).all()
    return render_template('tasks/list.html', tasks=tasks)

@tasks_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('Team Lead')
def create_task():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        start_date = request.form.get('start_date') or None
        due_date = request.form.get('due_date') or None
        priority = request.form.get('priority')
        required_skill_ids = request.form.getlist('required_skills')
        # Basic validation
        if not title:
            flash('Title is required.', 'danger')
            return redirect(request.url)
        task = Task(
            title=title,
            description=description,
            start_date=datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None,
            due_date=datetime.strptime(due_date, '%Y-%m-%d').date() if due_date else None,
            priority=priority,
            creator_id=current_user.employee.id,
        )
        # Attach required skills
        if required_skill_ids:
            skills = Skill.query.filter(Skill.id.in_(required_skill_ids)).all()
            task.required_skills = skills
        db.session.add(task)
        db.session.commit()
        # Recalculate deadline risk for the new task
        process_deadline_risk(task)
        flash('Task created successfully', 'success')
        return redirect(url_for('tasks.task_detail', task_id=task.id))
    # GET: render form
    all_skills = Skill.query.all()
    return render_template('tasks/form.html', skills=all_skills, action='Create')

@tasks_bp.route('/<int:task_id>')
@login_required
def task_detail(task_id):
    task = Task.query.get_or_404(task_id)
    # Authorization: employee can view if assigned, TL/Manager if owner or any
    if current_user.role.name == 'Employee':
        if current_user.employee not in task.assigned_employees:
            abort(403)
    elif current_user.role.name == 'Team Lead':
        if task.creator_id != current_user.employee.id:
            abort(403)
    # else Manager allowed
    recommendations = []
    if current_user.role.name == 'Team Lead' and not task.assigned_employees:
        recommendations = recommend_employees(task, db.session)
    workload_info = {}
    if current_user.role.name == 'Employee' and current_user.employee in task.assigned_employees:
        workload_info = compute_employee_workload(current_user.employee, db.session)
    deadline_risk = is_deadline_risk(task)
    return render_template('tasks/detail.html', task=task, recommendations=recommendations,
                           workload=workload_info, deadline_risk=deadline_risk)
@tasks_bp.route('/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Team Lead')
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    # Disallow editing completed tasks
    if task.status == TaskStatus.COMPLETED:
        abort(403)
    # Only the creator (Team Lead) can edit their tasks
    if task.creator_id != current_user.employee.id:
        abort(403)
    if request.method == 'POST':
        # Update fields only if they are present in form to prevent null overwrites
        title = request.form.get('title')
        if title:
            task.title = title
        description = request.form.get('description')
        if description is not None:
            task.description = description
        start_date = request.form.get('start_date')
        if start_date:
            task.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        due_date = request.form.get('due_date')
        if due_date:
            task.due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
        priority = request.form.get('priority')
        if priority:
            task.priority = priority
        required_skill_ids = request.form.getlist('required_skills')
        if required_skill_ids:
            task.required_skills = Skill.query.filter(Skill.id.in_(required_skill_ids)).all()
        db.session.commit()
        # Recalculate workload for assigned employee(s) after task edit
        for emp in task.assigned_employees:
            update_employee_workload(emp)
        # Recalculate deadline risk and create notifications if needed
        process_deadline_risk(task)
        flash('Task updated.', 'success')
        return redirect(url_for('tasks.task_detail', task_id=task.id))
    # GET request – render edit form
    all_skills = Skill.query.all()
    return render_template('tasks/form.html', task=task, skills=all_skills, action='Edit')

@tasks_bp.route('/<int:task_id>/assign', methods=['POST'])
@login_required
@role_required('Team Lead')
def assign_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.creator_id != current_user.employee.id:
        abort(403)
    employee_ids = request.form.getlist('employee_ids')
    if not employee_ids:
        flash('Select at least one employee to assign.', 'danger')
        return redirect(url_for('tasks.task_detail', task_id=task.id))
    # Clear previous assignments (reassignment case)
    previous_assignees = list(task.assigned_employees)
    task.assigned_employees = []
    for emp_id in employee_ids:
        emp = Employee.query.get(int(emp_id))
        if emp:
            task.assigned_employees.append(emp)
            # Notification for new assignee
            notif = Notification(recipient_id=emp.id,
                                 message=f'You have been assigned to task "{task.title}".')
            db.session.add(notif)
    # Notify removed assignees
    removed_ids = {e.id for e in previous_assignees} - {int(i) for i in employee_ids}
    for rm_id in removed_ids:
        rm_emp = Employee.query.get(rm_id)
        if rm_emp:
            notif = Notification(recipient_id=rm_emp.id,
                                 message=f'You have been unassigned from task "{task.title}".')
            db.session.add(notif)
    # Commit changes and recalculate workloads and deadline risk
    db.session.commit()
    # Recalculate workload for newly assigned employees
    for emp in task.assigned_employees:
        update_employee_workload(emp)
    # Recalculate workload for employees who were unassigned
    for rm_id in removed_ids:
        rm_emp = Employee.query.get(rm_id)
        if rm_emp:
            update_employee_workload(rm_emp)
    # Recalculate deadline risk for the task and notify if high
    process_deadline_risk(task)
    flash('Task assignment updated.', 'success')
    return redirect(url_for('tasks.task_detail', task_id=task.id))


@tasks_bp.route('/<int:task_id>/progress', methods=['POST'])
@login_required
@role_required('Employee')
def update_progress(task_id):
    task = Task.query.get_or_404(task_id)
    if current_user.employee not in task.assigned_employees:
        abort(403)
    try:
        progress = int(request.form.get('progress', 0))
    except ValueError:
        flash('Invalid progress value.', 'danger')
        return redirect(url_for('tasks.task_detail', task_id=task.id))
    # Validate progress range
    if progress < 0:
        flash('Invalid progress value.', 'danger')
        return redirect(url_for('tasks.task_detail', task_id=task.id))
    # Clamp progress to 0-100
    progress = max(0, min(100, progress))
    task.progress = progress
    # Auto‑update status based on progress
    if progress == 100:
        task.status = TaskStatus.COMPLETED
    elif progress > 0:
        task.status = TaskStatus.IN_PROGRESS
    db.session.commit()
    # Recalculate workload for assigned employee(s) after progress update
    for emp in task.assigned_employees:
        update_employee_workload(emp)
    flash('Progress updated.', 'success')
    return redirect(url_for('tasks.task_detail', task_id=task.id))

# Manager overview route
@tasks_bp.route('/manager/overview')
@login_required
@role_required('Manager')
def manager_overview():
    tasks = Task.query.all()
    # Compute workload distribution for each employee
    employees = Employee.query.all()
    workload_map = {e.id: compute_employee_workload(e, db.session) for e in employees}
    return render_template('manager/tasks_overview.html', tasks=tasks, workloads=workload_map)
