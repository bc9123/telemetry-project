"""webhook deliveries

Revision ID: f68fc9f4d218
Revises: 12be67633483
Create Date: 2026-01-11 12:09:36.796907

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f68fc9f4d218'
down_revision: Union[str, Sequence[str], None] = '12be67633483'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),

        sa.Column("alert_id", sa.Integer(), sa.ForeignKey("alerts.id"), nullable=False),
        sa.Column("webhook_id", sa.Integer(), sa.ForeignKey("webhook_subscriptions.id"), nullable=False),

        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),

        sa.Column("last_status_code", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),

        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),

        sa.UniqueConstraint("alert_id", "webhook_id", name="uq_delivery_alert_webhook"),
    )
    op.create_index("ix_delivery_project_created", "webhook_deliveries", ["project_id", "created_at"])
    op.create_index("ix_delivery_project_status", "webhook_deliveries", ["project_id", "status"])
    op.create_index("ix_delivery_alert_id", "webhook_deliveries", ["alert_id"])
    op.create_index("ix_delivery_project_id", "webhook_deliveries", ["project_id"])

def downgrade():
    op.drop_index("ix_delivery_project_id", table_name="webhook_deliveries")
    op.drop_index("ix_delivery_alert_id", table_name="webhook_deliveries")
    op.drop_index("ix_delivery_project_status", table_name="webhook_deliveries")
    op.drop_index("ix_delivery_project_created", table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")

