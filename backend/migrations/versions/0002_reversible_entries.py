"""Keep deleted entries recoverable while excluding them from the live ledger."""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("ledger_entries", sa.Column("revoked_at", sa.DateTime(), nullable=True))
    op.create_index("ix_ledger_entries_user_revoked", "ledger_entries", ["user_id", "revoked_at"])

def downgrade():
    op.drop_index("ix_ledger_entries_user_revoked", table_name="ledger_entries")
    op.drop_column("ledger_entries", "revoked_at")
