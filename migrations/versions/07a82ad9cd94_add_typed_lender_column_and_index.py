"""Add typed lender column and B-tree index."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "07a82ad9cd94"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "0899d658d997"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add lender column, backfill it, and create its index."""

    op.add_column(
        "documents",
        sa.Column("lender", sa.String(length=200), nullable=True),
    )

    # Copy existing lender values from JSONB into the typed column.
    op.execute(
        sa.text(
            """
            UPDATE documents
            SET lender = metadata ->> 'lender'
            WHERE metadata ? 'lender'
            """
        )
    )

    # Remove the duplicated lender value from JSONB.
    op.execute(
        sa.text(
            """
            UPDATE documents
            SET metadata = metadata - 'lender'
            WHERE metadata ? 'lender'
            """
        )
    )

    op.create_index(
        "ix_documents_lender",
        "documents",
        ["lender"],
        unique=False,
    )


def downgrade() -> None:
    """Restore lender values to JSONB before removing the typed column."""

    op.execute(
        sa.text(
            """
            UPDATE documents
            SET metadata = jsonb_set(
                metadata,
                '{lender}',
                to_jsonb(lender),
                true
            )
            WHERE lender IS NOT NULL
            """
        )
    )

    op.drop_index("ix_documents_lender", table_name="documents")
    op.drop_column("documents", "lender")
