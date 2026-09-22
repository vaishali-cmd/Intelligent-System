from ..extensions import db
from datetime import datetime
from sqlalchemy import Enum
import enum

class TaskPriority(enum.Enum):
    LOW = 'Low'
    MEDIUM = 'Medium'
    HIGH = 'High'
    CRITICAL = 'Critical'

class TaskStatus(enum.Enum):
    PENDING = 'Pending'
    IN_PROGRESS = 'In Progress'
    COMPLETED = 'Completed'
    BLOCKED = 'Blocked'

# Association table for required skills per task
task_skills = db.Table(
    'task_skills',
    db.Column('task_id', db.Integer, db.ForeignKey('tasks.id'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey('skills.id'), primary_key=True)
)

class Task(db.Model):
    __tablename__ = 'tasks'
    # Owner/creator of the task (Team Lead employee)
    creator_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    start_date = db.Column(db.Date, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    priority = db.Column(Enum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False)
    status = db.Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    progress = db.Column(db.Integer, default=0)  # 0-100 percent
    remarks = db.Column(db.Text)

    # Relationships
    required_skills = db.relationship('Skill', secondary=task_skills, backref='required_for_tasks')
    assigned_employees = db.relationship('Employee', secondary='task_assignments', back_populates='tasks')
    creator = db.relationship('Employee', foreign_keys=[creator_id], backref='created_tasks')

    def __repr__(self):
        return f"<Task {self.title}>"
