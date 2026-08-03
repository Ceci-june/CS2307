"""Recognize databases provisioned with the 20260803 compatibility revision.

The application schema represented by this revision is the same schema managed
by the initial search migration. Some provisioned databases were stamped with
``20260803_0004``; retaining that revision identifier lets Alembic start against
those databases while keeping fresh database upgrades deterministic.

Revision ID: 20260803_0004
Revises: 20260730_0001
"""

from typing import Union


revision: str = "20260803_0004"
down_revision: Union[str, None] = "20260730_0001"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
