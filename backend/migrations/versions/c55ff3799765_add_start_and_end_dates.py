"""add start and end dates

Revision ID: c55ff3799765
Revises: 
Create Date: 2024-03-19 22:29:21.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c55ff3799765'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Обновляем существующие значения status
    op.execute("""
        UPDATE tasks 
        SET status = CASE 
            WHEN status = 'TODO' THEN 'CREATED'
            WHEN status = 'IN_PROGRESS' THEN 'IN_PROGRESS'
            WHEN status = 'DONE' THEN 'DONE'
            ELSE 'CREATED'
        END
    """)


def downgrade() -> None:
    # Возвращаем старые значения status
    op.execute("""
        UPDATE tasks 
        SET status = CASE 
            WHEN status = 'CREATED' THEN 'TODO'
            WHEN status = 'IN_PROGRESS' THEN 'IN_PROGRESS'
            WHEN status = 'TESTING' THEN 'IN_PROGRESS'
            WHEN status = 'REVISION' THEN 'IN_PROGRESS'
            WHEN status = 'UPDATE' THEN 'IN_PROGRESS'
            WHEN status = 'DONE' THEN 'DONE'
            ELSE 'TODO'
        END
    """)
