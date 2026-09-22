from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from ..utils.decorators import role_required
from ..utils.assignment import recommend_employees
from ..utils.notify import notify_employee
from ..models import Task, Employee
from ..extensions import db

lead_bp = Blueprint('team_lead', __name__)

@lead_bp.route('/dashboard')
@role_required('Team Lead')
@login_required
def dashboard():
    emp = getattr(current_user, 'employee', None)
    created_tasks = Task.query.filter_by(creator_id=emp.id).all() if emp else []
    if not created_tasks:
        created_tasks = Task.query.all()
        
    from ..models import Team, Skill
    team = Team.query.filter_by(lead_id=emp.id).first() if emp else None
    team_members = team.members if team else Employee.query.filter(Employee.id != (emp.id if emp else -1)).all()
    skills = Skill.query.all()
    
    return render_template(
        'team_lead/dashboard.html',
        lead=emp,
        team=team,
        team_members=team_members,
        tasks=created_tasks,
        skills=skills,
        current_user=current_user
    )

# ---------- Smart Assignment ----------
@lead_bp.route('/task/<int:task_id>/recommendations')
@role_required('Team Lead')
@login_required
def recommendations(task_id):
    task = Task.query.get_or_404(task_id)
    # Only the creator (Team Lead) can view recommendations
    if task.creator_id != current_user.employee.id:
        abort(403)
    recs = recommend_employees(task, db.session)
    # Show top N recommendations only
    TOP_N = 5
    recs = recs[:TOP_N]
    return render_template('team_lead/recommendations.html', task=task, recommendations=recs)

@lead_bp.route('/task/<int:task_id>/assign', methods=['POST'])
@role_required('Team Lead')
@login_required
def assign(task_id):
    task = Task.query.get_or_404(task_id)
    if task.creator_id != current_user.employee.id:
        abort(403)
    # Expect a list of employee IDs from the form
    emp_ids = request.form.getlist('employee_id')
    if not emp_ids:
        flash('No employees selected for assignment.', 'error')
        return redirect(url_for('.recommendations', task_id=task_id))
    for emp_id in emp_ids:
        emp = Employee.query.get(int(emp_id))
        if emp and emp not in task.assigned_employees:
            task.assigned_employees.append(emp)
            notify_employee(emp.id, f'You have been assigned to task "{task.title}".')
    db.session.commit()
    flash('Employees assigned successfully.', 'info')
    return redirect(url_for('tasks.task_detail', task_id=task.id))

@lead_bp.route('/task/<int:task_id>/reassign', methods=['POST'])
@role_required('Team Lead')
@login_required
def reassign(task_id):
    task = Task.query.get_or_404(task_id)
    if task.creator_id != current_user.employee.id:
        abort(403)
    new_ids = set(map(int, request.form.getlist('employee_id')))
    current_ids = {emp.id for emp in task.assigned_employees}
    to_add = new_ids - current_ids
    to_remove = current_ids - new_ids
    for emp_id in to_add:
        emp = Employee.query.get(emp_id)
        if emp:
            task.assigned_employees.append(emp)
            notify_employee(emp.id, f'You have been assigned to task "{task.title}".')
    for emp_id in to_remove:
        emp = Employee.query.get(emp_id)
        if emp:
            task.assigned_employees.remove(emp)
            notify_employee(emp.id, f'You have been unassigned from task "{task.title}".')
    db.session.commit()
    flash('Task reassignments updated.', 'info')
    return redirect(url_for('tasks.task_detail', task_id=task.id))
