"""add transfer_in value to transaction_type enum

Revision ID: c1001ae3cd8c
Revises: 1df65bc21ca9
Create Date: 2026-08-19 12:19:52.330190

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1001ae3cd8c'
down_revision: Union[str, Sequence[str], None] = '1df65bc21ca9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE transaction_type ADD VALUE IF NOT EXISTS 'transfer_in'")
    


def downgrade() -> None:
    """Downgrade schema."""
    pass
