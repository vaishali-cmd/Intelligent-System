from ..extensions import db
from datetime import datetime
import enum

class LeaveType(enum.Enum):
    CASUAL = 'Casual Leave'
    SICK = 'Sick Leave'
    PAID = 'Paid Time Off'
    EMERGENCY = 'Emergency Leave'

class LeaveStatus(enum.Enum):
    PENDING = 'Pending'
    APPROVED = 'Approved'
    REJECTED = 'Rejected'

class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    leave_type = db.Column(db.String(50), default='Casual Leave', nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='Pending', nullable=False)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    employee = db.relationship('Employee', foreign_keys=[employee_id], backref=db.backref('leave_requests', lazy='dynamic', cascade='all, delete-orphan'))
    reviewer = db.relationship('Employee', foreign_keys=[reviewed_by_id])

    def __repr__(self):
        return f"<LeaveRequest {self.id} emp={self.employee_id} status={self.status}>"
