from ..extensions import db
from datetime import datetime

# Association table for many-to-many relationship between teams and employees
team_members = db.Table(
    'team_members',
    db.Column('team_id', db.Integer, db.ForeignKey('teams.id'), primary_key=True),
    db.Column('employee_id', db.Integer, db.ForeignKey('employees.id'), primary_key=True)
)

class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    lead_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    manager = db.relationship('Employee', foreign_keys=[manager_id], backref='managed_teams')
    lead = db.relationship('Employee', foreign_keys=[lead_id], backref='lead_teams')
    members = db.relationship('Employee', secondary=team_members, backref='teams')

    def __repr__(self):
        return f"<Team {self.name}>"
