from flask import Blueprint, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from ..extensions import db
from ..models import LeaveRequest, Employee
from ..utils.decorators import role_required

leave_bp = Blueprint('leave', __name__, url_prefix='/leave')

@leave_bp.route('/request', methods=['POST'])
@login_required
def submit_request():
    emp = getattr(current_user, 'employee', None)
    if not emp:
        flash('You must have an employee profile to request leave.', 'error')
        return redirect(request.referrer or url_for('employee.dashboard'))

    leave_type = request.form.get('leave_type', 'Casual Leave')
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    reason = request.form.get('reason', '')

    if not start_date_str or not end_date_str:
        flash('Start date and end date are required.', 'error')
        return redirect(request.referrer or url_for('employee.dashboard'))

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date format.', 'error')
        return redirect(request.referrer or url_for('employee.dashboard'))

    if end_date < start_date:
        flash('End date cannot be earlier than start date.', 'error')
        return redirect(request.referrer or url_for('employee.dashboard'))

    req = LeaveRequest(
        employee_id=emp.id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        status='Pending'
    )
    db.session.add(req)
    db.session.commit()
    flash(f'Leave request submitted successfully for {start_date} to {end_date}.', 'success')
    return redirect(request.referrer or url_for('employee.dashboard'))

@leave_bp.route('/<int:leave_id>/approve', methods=['POST'])
@login_required
def approve_request(leave_id):
    # Only Manager, HR, Admin, or Team Lead can approve
    user_role = getattr(getattr(current_user, 'role', None), 'name', None)
    if user_role not in ('Manager', 'HR', 'Admin', 'Team Lead'):
        flash('Permission denied. Only leadership can approve leave.', 'error')
        abort(403)

    leave = LeaveRequest.query.get_or_404(leave_id)
    leave.status = 'Approved'
    emp = getattr(current_user, 'employee', None)
    if emp:
        leave.reviewed_by_id = emp.id
    db.session.commit()
    flash(f'Leave request #{leave.id} for {leave.employee.full_name} has been APPROVED.', 'success')
    return redirect(request.referrer or url_for('manager.dashboard'))

@leave_bp.route('/<int:leave_id>/reject', methods=['POST'])
@login_required
def reject_request(leave_id):
    user_role = getattr(getattr(current_user, 'role', None), 'name', None)
    if user_role not in ('Manager', 'HR', 'Admin', 'Team Lead'):
        flash('Permission denied. Only leadership can reject leave.', 'error')
        abort(403)

    leave = LeaveRequest.query.get_or_404(leave_id)
    leave.status = 'Rejected'
    emp = getattr(current_user, 'employee', None)
    if emp:
        leave.reviewed_by_id = emp.id
    db.session.commit()
    flash(f'Leave request #{leave.id} for {leave.employee.full_name} has been REJECTED.', 'info')
    return redirect(request.referrer or url_for('manager.dashboard'))

@leave_bp.route('/<int:leave_id>/cancel', methods=['POST'])
@login_required
def cancel_request(leave_id):
    leave = LeaveRequest.query.get_or_404(leave_id)
    emp = getattr(current_user, 'employee', None)
    if not emp or leave.employee_id != emp.id:
        flash('You cannot cancel another employee\'s leave request.', 'error')
        abort(403)

    if leave.status != 'Pending':
        flash('Only pending leave requests can be cancelled.', 'error')
        return redirect(request.referrer or url_for('employee.dashboard'))

    db.session.delete(leave)
    db.session.commit()
    flash('Leave request cancelled successfully.', 'info')
    return redirect(request.referrer or url_for('employee.dashboard'))
