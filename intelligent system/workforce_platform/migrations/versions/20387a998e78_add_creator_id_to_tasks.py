"""Add creator_id to tasks

Revision ID: 20387a998e78
Revises: 7a2f1fc423cc
Create Date: 2026-09-20 22:07:29.261072
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20387a998e78'
down_revision = '7a2f1fc423cc'
branch_labels = None
depends_on = None


def upgrade():
    # Add creator_id column to tasks with foreign key to employees
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('creator_id', sa.Integer(), nullable=False))
        batch_op.create_foreign_key('fk_tasks_creator_id_employees', 'employees', ['creator_id'], ['id'])


def downgrade():
    # Remove creator_id column and foreign key
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_constraint('fk_tasks_creator_id_employees', type_='foreignkey')
        batch_op.drop_column('creator_id')
