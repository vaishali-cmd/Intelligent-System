from ..extensions import db
from datetime import datetime

# Association tables for many-to-many relationships
employee_skills = db.Table(
    'employee_skills',
    db.Column('employee_id', db.Integer, db.ForeignKey('employees.id'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey('skills.id'), primary_key=True)
)

task_assignments = db.Table(
    'task_assignments',
    db.Column('employee_id', db.Integer, db.ForeignKey('employees.id'), primary_key=True),
    db.Column('task_id', db.Integer, db.ForeignKey('tasks.id'), primary_key=True)
)

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    # Optional derived full_name property
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    phone = db.Column(db.String(20))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'))
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'))  # self-referential
    lead_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    joining_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    department = db.relationship('Department', foreign_keys=[department_id], back_populates='employees')
    team = db.relationship('Team', foreign_keys=[team_id])
    manager = db.relationship('Employee', remote_side=[id], backref='managed_employees', foreign_keys=[manager_id])
    lead = db.relationship('Employee', remote_side=[id], backref='lead_employees', foreign_keys=[lead_id])
    skills = db.relationship('Skill', secondary=employee_skills, backref='employees')
    tasks = db.relationship('Task', secondary=task_assignments, back_populates='assigned_employees')
# Placeholder relationships - to be added when corresponding models are implemented
# attendances = db.relationship('Attendance', backref='employee', lazy='dynamic')
# leave_requests = db.relationship('LeaveRequest', backref='employee', lazy='dynamic')
    notifications = db.relationship('Notification', back_populates='employee', lazy='dynamic')
# performance_records = db.relationship('PerformanceRecord', backref='employee', lazy='dynamic')

    def __repr__(self):
        return f"<Employee {self.full_name}>"
