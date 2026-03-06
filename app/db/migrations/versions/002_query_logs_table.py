"""Query logs table and drop old agent_run_logs.

Revision ID: 002
Revises: 001
Create Date: 2026-03-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # Drop legacy agent_run_logs table if it exists.
    if "agent_run_logs" in existing_tables:
        op.drop_table("agent_run_logs")

    # Create new query_logs table.
    op.create_table(
        "query_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("session_id", sa.String(36), nullable=True, index=True),
        sa.Column("user_query", sa.Text(), nullable=False),
        sa.Column("sql_query", sa.Text(), nullable=True),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    # Drop new query_logs table.
    op.drop_table("query_logs")

