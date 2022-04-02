"""urls table fetched

Revision ID: c8d3d789bd34
Revises: f3a0e8320ef9
Create Date: 2022-04-02 19:52:02.644182

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c8d3d789bd34'
down_revision = 'f3a0e8320ef9'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('urls', sa.Column('fetched', sa.DateTime(), server_default=sa.text('now()'), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('urls', 'fetched')
    # ### end Alembic commands ###