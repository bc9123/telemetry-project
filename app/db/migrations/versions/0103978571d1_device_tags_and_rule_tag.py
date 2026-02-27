"""device tags and rule tag

Revision ID: 0103978571d1
Revises: 1da9104c4b26
Create Date: 2026-01-11 07:35:51.496381

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0103978571d1'
down_revision: Union[str, Sequence[str], None] = '1da9104c4b26'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "devices",
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.alter_column("devices", "tags", server_default=None)
    op.create_index('ix_devices_project_external', 'devices', ['project_id', 'external_id'], unique=False)
    op.create_index('ix_devices_project_id', 'devices', ['project_id'], unique=False)
    op.add_column('rules', sa.Column('tag', sa.String(length=64), nullable=True))
    op.create_index('ix_rules_project_enabled', 'rules', ['project_id', 'enabled'], unique=False)
    op.create_index('ix_rules_project_scope', 'rules', ['project_id', 'scope'], unique=False)
    op.create_index('ix_telemetry_device_ts', 'telemetry_events', ['device_id', 'ts'], unique=False)
    op.execute("CREATE INDEX IF NOT EXISTS ix_devices_tags_gin ON devices USING GIN (tags)")



def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_devices_tags_gin")
    op.drop_index("ix_telemetry_device_ts", table_name="telemetry_events")
    op.drop_index("ix_rules_project_scope", table_name="rules")
    op.drop_index("ix_rules_project_enabled", table_name="rules")
    op.drop_column("rules", "tag")
    op.drop_index("ix_devices_project_id", table_name="devices")
    op.drop_index("ix_devices_project_external", table_name="devices")
    op.drop_column("devices", "tags")

