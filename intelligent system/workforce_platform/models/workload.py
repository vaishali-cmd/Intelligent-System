from datetime import datetime

from ..extensions import db


class Workload(db.Model):
    __tablename__ = "workloads"

    id = db.Column(db.Integer, primary_key=True)

    employee_id = db.Column(
        db.Integer,
        db.ForeignKey("employees.id"),
        nullable=False,
        unique=True,
    )

    total_hours = db.Column(
        db.Float,
        nullable=False,
        default=0.0,
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="Low",
    )

    last_calculated = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    employee = db.relationship(
        "Employee",
        backref=db.backref("workload", uselist=False),
    )

    def __repr__(self):
        return (
            f"<Workload employee_id={self.employee_id} "
            f"status={self.status}>"
        )
