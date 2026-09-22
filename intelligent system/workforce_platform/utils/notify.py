from ..extensions import db
from ..models.notification import Notification


def notify_employee(employee_id: int, message: str) -> None:
    """Create a notification for the given employee.

    Args:
        employee_id (int): The ID of the employee to notify.
        message (str): Notification message.
    """
    notif = Notification(recipient_id=employee_id, message=message)
    db.session.add(notif)
    db.session.commit()
