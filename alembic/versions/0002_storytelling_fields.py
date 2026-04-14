"""storytelling and decorative fields

Revision ID: 0002_storytelling_fields
Revises: 0001_initial
Create Date: 2026-04-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_storytelling_fields"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("categories", sa.Column("story_intro", sa.Text(), nullable=True))
    op.add_column("categories", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"))
    op.add_column("categories", sa.Column("show_on_landing", sa.Boolean(), nullable=False, server_default=sa.true()))

    op.add_column("media_files", sa.Column("is_decorative", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("media_files", sa.Column("decor_usage", sa.String(length=64), nullable=True))
    op.add_column("media_files", sa.Column("show_on_landing", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("media_files", sa.Column("display_order", sa.Integer(), nullable=False, server_default="100"))


def downgrade() -> None:
    op.drop_column("media_files", "display_order")
    op.drop_column("media_files", "show_on_landing")
    op.drop_column("media_files", "decor_usage")
    op.drop_column("media_files", "is_decorative")

    op.drop_column("categories", "show_on_landing")
    op.drop_column("categories", "sort_order")
    op.drop_column("categories", "story_intro")
