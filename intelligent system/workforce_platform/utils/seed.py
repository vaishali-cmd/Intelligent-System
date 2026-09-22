import os
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash
from ..extensions import db
from ..models import (
    User, Role, Employee, Department, Team, Skill, Task, 
    TaskPriority, TaskStatus, Attendance, Notification
)

def seed_database():
    """Seeds the database with standard roles, 4 role login accounts, and sample workforce data."""
    # 1. Create or get Roles
    roles_list = ['HR', 'Admin', 'Manager', 'Team Lead', 'Employee']
    roles_dict = {}
    for r_name in roles_list:
        role = Role.query.filter_by(name=r_name).first()
        if not role:
            role = Role(name=r_name)
            db.session.add(role)
            db.session.flush()
        roles_dict[r_name] = role

    # 2. Departments
    dept_names = ['Engineering', 'Product & Design', 'Human Resources', 'Operations']
    depts_dict = {}
    for d_name in dept_names:
        dept = Department.query.filter_by(name=d_name).first()
        if not dept:
            dept = Department(name=d_name)
            db.session.add(dept)
            db.session.flush()
        depts_dict[d_name] = dept

    # 3. Skills
    skills_list = ['Python', 'Flask', 'React', 'SQL', 'DevOps & CI/CD', 'UI/UX Design', 'System Architecture', 'Agile Delivery']
    skills_dict = {}
    for s_name in skills_list:
        skill = Skill.query.filter_by(name=s_name).first()
        if not skill:
            skill = Skill(name=s_name)
            db.session.add(skill)
            db.session.flush()
        skills_dict[s_name] = skill

    # 4. Standard 4 Accounts definitions
    accounts = [
        {
            'email': 'admin@workforce.com',
            'password': 'admin123',
            'role': 'HR',
            'first_name': 'Eleanor',
            'last_name': 'Vance',
            'phone': '+1 555-0101',
            'dept': 'Human Resources',
            'status': 'active'
        },
        {
            'email': 'manager@workforce.com',
            'password': 'manager123',
            'role': 'Manager',
            'first_name': 'Marcus',
            'last_name': 'Sterling',
            'phone': '+1 555-0102',
            'dept': 'Engineering',
            'status': 'active'
        },
        {
            'email': 'lead@workforce.com',
            'password': 'lead123',
            'role': 'Team Lead',
            'first_name': 'Sarah',
            'last_name': 'Chen',
            'phone': '+1 555-0103',
            'dept': 'Engineering',
            'status': 'active'
        },
        {
            'email': 'employee@workforce.com',
            'password': 'employee123',
            'role': 'Employee',
            'first_name': 'Alex',
            'last_name': 'Rivera',
            'phone': '+1 555-0104',
            'dept': 'Engineering',
            'status': 'active'
        },
        # Supporting teammate
        {
            'email': 'dev2@workforce.com',
            'password': 'dev123',
            'role': 'Employee',
            'first_name': 'Priya',
            'last_name': 'Patel',
            'phone': '+1 555-0105',
            'dept': 'Engineering',
            'status': 'active'
        }
    ]

    emp_dict = {}
    for acc in accounts:
        user = User.query.filter_by(email=acc['email']).first()
        if not user:
            user = User(
                email=acc['email'],
                password_hash=generate_password_hash(acc['password']),
                role=roles_dict[acc['role']]
            )
            db.session.add(user)
            db.session.flush()
        else:
            # Ensure password and role are current
            user.password_hash = generate_password_hash(acc['password'])
            user.role = roles_dict[acc['role']]
            db.session.flush()

        emp = Employee.query.filter_by(user_id=user.id).first()
        if not emp:
            emp = Employee(
                user_id=user.id,
                first_name=acc['first_name'],
                last_name=acc['last_name'],
                phone=acc['phone'],
                department_id=depts_dict[acc['dept']].id,
                joining_date=date(2023, 1, 15),
                status=acc['status']
            )
            db.session.add(emp)
            db.session.flush()
        emp_dict[acc['email']] = emp

    # Set up Manager & Lead hierarchy
    manager_emp = emp_dict.get('manager@workforce.com')
    lead_emp = emp_dict.get('lead@workforce.com')
    worker_emp = emp_dict.get('employee@workforce.com')
    dev2_emp = emp_dict.get('dev2@workforce.com')

    if lead_emp and manager_emp:
        lead_emp.manager_id = manager_emp.id
    if worker_emp and lead_emp:
        worker_emp.lead_id = lead_emp.id
        worker_emp.manager_id = manager_emp.id if manager_emp else None
    if dev2_emp and lead_emp:
        dev2_emp.lead_id = lead_emp.id
        dev2_emp.manager_id = manager_emp.id if manager_emp else None

    # Assign skills to employees
    if worker_emp and not worker_emp.skills:
        worker_emp.skills = [skills_dict['Python'], skills_dict['Flask'], skills_dict['React'], skills_dict['SQL']]
    if dev2_emp and not dev2_emp.skills:
        dev2_emp.skills = [skills_dict['React'], skills_dict['UI/UX Design'], skills_dict['DevOps & CI/CD']]
    if lead_emp and not lead_emp.skills:
        lead_emp.skills = [skills_dict['Python'], skills_dict['System Architecture'], skills_dict['Agile Delivery']]

    # 5. Team
    eng_dept = depts_dict['Engineering']
    team = Team.query.filter_by(name='Core Platform Team').first()
    if not team:
        team = Team(
            name='Core Platform Team',
            department_id=eng_dept.id,
            manager_id=manager_emp.id if manager_emp else None,
            lead_id=lead_emp.id if lead_emp else None
        )
        db.session.add(team)
        db.session.flush()
    if worker_emp and worker_emp not in team.members:
        team.members.append(worker_emp)
    if dev2_emp and dev2_emp not in team.members:
        team.members.append(dev2_emp)

    # 6. Sample Tasks created by Lead
    if lead_emp:
        existing_tasks = Task.query.filter_by(creator_id=lead_emp.id).count()
        if existing_tasks == 0:
            today = date.today()
            t1 = Task(
                creator_id=lead_emp.id,
                title='Implement OAuth2 & Single Sign-On Architecture',
                description='Upgrade platform security with OAuth2 token providers and encrypted session cookies.',
                start_date=today - timedelta(days=2),
                due_date=today + timedelta(days=5),
                priority=TaskPriority.HIGH,
                status=TaskStatus.IN_PROGRESS,
                progress=65,
                remarks='Security audit passed. Finalizing callback routes.'
            )
            t1.required_skills = [skills_dict['Python'], skills_dict['Flask']]
            if worker_emp:
                t1.assigned_employees.append(worker_emp)

            t2 = Task(
                creator_id=lead_emp.id,
                title='AI-Powered Smart Task Assignment Engine',
                description='Build automated recommendation heuristics matching team member skills, availability, and active workloads.',
                start_date=today - timedelta(days=1),
                due_date=today + timedelta(days=3),
                priority=TaskPriority.CRITICAL,
                status=TaskStatus.IN_PROGRESS,
                progress=40,
                remarks='Prototype running in test suite.'
            )
            t2.required_skills = [skills_dict['Python'], skills_dict['SQL'], skills_dict['System Architecture']]
            if worker_emp:
                t2.assigned_employees.append(worker_emp)

            t3 = Task(
                creator_id=lead_emp.id,
                title='Frontend Responsive Glassmorphic UI Revamp',
                description='Redesign dashboard interfaces with rich dark SaaS aesthetics, micro-interactions, and role widgets.',
                start_date=today,
                due_date=today + timedelta(days=7),
                priority=TaskPriority.MEDIUM,
                status=TaskStatus.PENDING,
                progress=15,
                remarks='Mockups ready for implementation.'
            )
            t3.required_skills = [skills_dict['React'], skills_dict['UI/UX Design']]
            if dev2_emp:
                t3.assigned_employees.append(dev2_emp)

            t4 = Task(
                creator_id=lead_emp.id,
                title='Database Performance Tuning & Index Optimization',
                description='Optimize slow queries, add indexes on high-frequency tables (users, tasks, attendances).',
                start_date=today - timedelta(days=10),
                due_date=today - timedelta(days=1),
                priority=TaskPriority.LOW,
                status=TaskStatus.COMPLETED,
                progress=100,
                remarks='Delivered ahead of schedule. Query latency reduced by 48%.'
            )
            t4.required_skills = [skills_dict['SQL'], skills_dict['DevOps & CI/CD']]
            if worker_emp:
                t4.assigned_employees.append(worker_emp)

            db.session.add_all([t1, t2, t3, t4])

    # 7. Today's Attendances
    today = date.today()
    for emp in [manager_emp, lead_emp, worker_emp, dev2_emp]:
        if emp:
            att = Attendance.query.filter_by(employee_id=emp.id, date=today).first()
            if not att:
                att = Attendance(employee_id=emp.id, date=today, status='present')
    # 8. Sample Leave Requests
    from ..models import LeaveRequest
    if worker_emp and LeaveRequest.query.count() == 0:
        today = date.today()
        l1 = LeaveRequest(
            employee_id=worker_emp.id,
            leave_type='Paid Time Off',
            start_date=today + timedelta(days=7),
            end_date=today + timedelta(days=9),
            reason='Family annual gathering and vacation.',
            status='Pending'
        )
        if dev2_emp:
            l2 = LeaveRequest(
                employee_id=dev2_emp.id,
                leave_type='Sick Leave',
                start_date=today - timedelta(days=5),
                end_date=today - timedelta(days=4),
                reason='Doctor consultation and medical rest.',
                status='Approved',
                reviewed_by_id=manager_emp.id if manager_emp else None
            )
            db.session.add(l2)
        db.session.add(l1)

    db.session.commit()
    print("Database successfully seeded with 4 role logins and sample workforce data!")
