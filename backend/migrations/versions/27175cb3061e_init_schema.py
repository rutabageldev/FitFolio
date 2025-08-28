"""init schema

Revision ID: 27175cb3061e
Revises:
Create Date: 2025-08-09 15:31:10.805774

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "27175cb3061e"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
