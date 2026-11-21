"""Structured relationship fields and durable import identities."""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("ledger_entries", sa.Column("counterparty", sa.String(80), nullable=False, server_default=""))
    op.add_column("ledger_entries", sa.Column("event", sa.String(120), nullable=False, server_default=""))
    op.add_column("ledger_entries", sa.Column("import_source", sa.String(80), nullable=True))
    op.add_column("ledger_entries", sa.Column("external_id", sa.String(100), nullable=True))
    op.create_unique_constraint("uq_ledger_import_record", "ledger_entries", ["user_id", "import_source", "external_id"])

def downgrade():
    op.drop_constraint("uq_ledger_import_record", "ledger_entries", type_="unique")
    for name in ["external_id", "import_source", "event", "counterparty"]:
        op.drop_column("ledger_entries", name)
