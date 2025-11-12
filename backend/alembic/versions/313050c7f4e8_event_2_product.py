"""Event 2 Product

Revision ID: 313050c7f4e8
Revises: f42aba4d8562
Create Date: 2025-11-12 14:59:18.009094

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '313050c7f4e8'
down_revision: Union[str, Sequence[str], None] = 'f42aba4d8562'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Disable foreign key checks (SQLite requires this)
    op.execute("PRAGMA foreign_keys=OFF;")

    conn = op.get_bind().connection
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    table_names = [t[0] for t in tables]

    if 'events' in table_names:
        op.execute("ALTER TABLE events RENAME TO products;")

    if 'event_customers' in table_names:
        op.execute("ALTER TABLE event_customers RENAME TO product_customers;")

    # --- Rename columns in product_customers ---
    with op.batch_alter_table("product_customers") as batch_op:
        batch_op.alter_column("event_id", new_column_name="product_id")

    # --- Rename column in alarms ---
    with op.batch_alter_table("alarms") as batch_op:
        batch_op.alter_column("event_id", new_column_name="product_id")

    # Re-enable foreign keys
    op.execute("PRAGMA foreign_keys=ON;")


def downgrade():
    op.execute("PRAGMA foreign_keys=OFF;")

    # Rename columns back
    with op.batch_alter_table("product_customers") as batch_op:
        batch_op.alter_column("product_id", new_column_name="event_id")

    with op.batch_alter_table("alarms") as batch_op:
        batch_op.alter_column("product_id", new_column_name="event_id")

    # Rename tables back
    op.execute("ALTER TABLE product_customers RENAME TO event_customers;")
    op.execute("ALTER TABLE products RENAME TO events;")

    op.execute("PRAGMA foreign_keys=ON;")
