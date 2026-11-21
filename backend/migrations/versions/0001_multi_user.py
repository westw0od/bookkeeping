"""Initial multi-user MySQL schema; never auto-assign the old SQLite ledger."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("users", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(40), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("default_key_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("login_sessions", sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_login_sessions_user_id", "login_sessions", ["user_id"])
    op.create_index("ix_login_sessions_expires_at", "login_sessions", ["expires_at"])
    op.create_table("ledger_entries", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.String(36), nullable=False), sa.Column("type", sa.String(7), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False), sa.Column("category", sa.String(30), nullable=False),
        sa.Column("note", sa.Text(), nullable=False), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "client_id"), sa.CheckConstraint("amount_cents > 0"),
        sa.CheckConstraint("type IN ('income', 'expense')"))
    op.create_index("ix_ledger_entries_user_id", "ledger_entries", ["user_id"])
    op.create_index("ix_ledger_entries_occurred_at", "ledger_entries", ["occurred_at"])
    op.create_table("personal_categories", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(7), nullable=False), sa.Column("name", sa.String(30), nullable=False),
        sa.UniqueConstraint("user_id", "type", "name"))
    op.create_index("ix_personal_categories_user_id", "personal_categories", ["user_id"])
    op.create_table("uploaded_images", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(80), nullable=False), sa.Column("mime", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_uploaded_images_user_id", "uploaded_images", ["user_id"])
    op.create_table("user_api_keys", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(50), nullable=False), sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("model", sa.String(100), nullable=False), sa.Column("vision_model", sa.String(100), nullable=True),
        sa.Column("encrypted_key", sa.Text(), nullable=False), sa.Column("suffix", sa.String(4), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_user_api_keys_user_id", "user_api_keys", ["user_id"])
    op.create_table("ai_usage", sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True), sa.Column("count", sa.Integer(), nullable=False))
    op.create_table("auth_attempts", sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("bucket", sa.BigInteger(), primary_key=True), sa.Column("count", sa.Integer(), nullable=False))

def downgrade():
    for table in ["auth_attempts", "ai_usage", "user_api_keys", "uploaded_images", "personal_categories", "ledger_entries", "login_sessions", "users"]:
        op.drop_table(table)
