"""update ck_content_type CHECK constraint to match current ContentType enum

Revision ID: j0k1l2m3n4o5
Revises: i9j0k1l2m3n4
Create Date: 2026-02-27 14:00:00.000000

The original CHECK constraint (created in a1b2c3d4e5f6) only allowed 7
content types.  The application now supports 13 content types after the
cross-pollination from gor-marketing added social_linkedin, email_just_listed,
email_open_house, email_drip, open_house_invite, price_reduction, and
just_sold.  The old names 'description' and 'email' were also replaced by
'listing_description' and the three email_* variants.

Source of truth: app.schemas.content.ContentType enum.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "j0k1l2m3n4o5"
down_revision: Union[str, None] = "i9j0k1l2m3n4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# All 13 content types from app.schemas.content.ContentType
NEW_CONTENT_TYPES = (
    "'listing_description',"
    "'social_instagram',"
    "'social_facebook',"
    "'social_linkedin',"
    "'social_x',"
    "'email_just_listed',"
    "'email_open_house',"
    "'email_drip',"
    "'flyer',"
    "'video_script',"
    "'open_house_invite',"
    "'price_reduction',"
    "'just_sold'"
)

# Original 7 types from migration a1b2c3d4e5f6
OLD_CONTENT_TYPES = (
    "'description',"
    "'social_instagram',"
    "'social_facebook',"
    "'social_x',"
    "'email',"
    "'flyer',"
    "'video_script'"
)


def upgrade() -> None:
    op.drop_constraint("ck_content_type", "content", type_="check")
    op.create_check_constraint(
        "ck_content_type", "content",
        f"content_type IN ({NEW_CONTENT_TYPES})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_content_type", "content", type_="check")
    op.create_check_constraint(
        "ck_content_type", "content",
        f"content_type IN ({OLD_CONTENT_TYPES})",
    )
