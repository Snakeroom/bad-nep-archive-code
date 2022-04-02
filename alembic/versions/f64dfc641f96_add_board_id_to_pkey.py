"""add board id to pkey

Revision ID: f64dfc641f96
Revises: 09b9ad5a95d8
Create Date: 2022-04-02 19:21:53.564174

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f64dfc641f96'
down_revision = '09b9ad5a95d8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('pixels', 'board_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.drop_index('pixel_unique_mod', table_name='pixels')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index('pixel_unique_mod', 'pixels', ['x', 'y', 'modified'], unique=False)
    op.alter_column('pixels', 'board_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    # ### end Alembic commands ###