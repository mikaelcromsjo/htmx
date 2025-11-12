"""Add last_call_date to customers

Revision ID: f42aba4d8562
Revises:
Create Date: 2025-11-12 13:05:57.087411
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import json
from datetime import datetime, timezone
from dateutil import parser  # more robust ISO parser

# revision identifiers, used by Alembic.
revision: str = "f42aba4d8562"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    print("[upgrade] Starting migration: adding last_call_date column")
    op.add_column("customers", sa.Column("last_call_date", sa.DateTime(timezone=True), nullable=True))

    connection = op.get_bind()
    customers = connection.execute(sa.text("SELECT id, extra FROM customers")).fetchall()
    print(f"[upgrade] Found {len(customers)} customers to inspect")

    for customer_id, extra_json in customers:
        if not extra_json:
            continue

        try:
            extra_data = json.loads(extra_json)
        except Exception as e:
            print(f"[upgrade] ⚠️ Could not parse JSON for customer {customer_id}: {e}")
            continue

        iso_date = extra_data.pop("last_call_date", None)

        if not iso_date:
#            print(f"[upgrade] Customer {customer_id}: no last_call_date in extra")
            continue

        try:
            dt = parser.isoparse(iso_date)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            print(f"[upgrade] Customer {customer_id}: migrating {iso_date} → {dt.isoformat()}")

            connection.execute(
                sa.text(
                    "UPDATE customers SET last_call_date = :dt, extra = :extra WHERE id = :id"
                ),
                {"dt": dt, "extra": json.dumps(extra_data), "id": customer_id},
            )
        except Exception as e:
            print(f"[upgrade] ⚠️ Failed to parse or update customer {customer_id}: {e}")

    print("[upgrade] ✅ Migration complete.")


def downgrade():
    print("[downgrade] Starting rollback: moving last_call_date back into extra")
    connection = op.get_bind()
    customers = connection.execute(sa.text("SELECT id, last_call_date, extra FROM customers")).fetchall()
    print(f"[downgrade] Found {len(customers)} customers to inspect")

    for customer_id, last_call_date, extra_json in customers:
        try:
            extra_data = json.loads(extra_json) if extra_json else {}
        except Exception as e:
            print(f"[downgrade] ⚠️ Could not parse JSON for customer {customer_id}: {e}")
            continue

        if not last_call_date:
            print(f"[downgrade] Customer {customer_id}: no last_call_date value, skipping")
            continue

        try:
            # Convert string → datetime if needed
            if isinstance(last_call_date, str):
                dt = parser.isoparse(last_call_date)
            else:
                dt = last_call_date

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            iso_date = dt.astimezone(timezone.utc).replace(second=0, microsecond=0).isoformat()
            extra_data["last_call_date"] = iso_date

            connection.execute(
                sa.text("UPDATE customers SET extra = :extra WHERE id = :id"),
                {"extra": json.dumps(extra_data), "id": customer_id},
            )
            print(f"[downgrade] Customer {customer_id}: restored last_call_date={iso_date}")
        except Exception as e:
            print(f"[downgrade] ⚠️ Failed to handle customer {customer_id}: {e}")

    op.drop_column("customers", "last_call_date")
    print("[downgrade] ✅ Rollback complete.")
