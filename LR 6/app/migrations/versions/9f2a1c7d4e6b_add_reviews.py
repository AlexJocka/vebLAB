"""Add reviews

Revision ID: 9f2a1c7d4e6b
Revises: 243ae1b0b6fe
Create Date: 2026-06-05 22:58:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f2a1c7d4e6b'
down_revision = '243ae1b0b6fe'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('reviews',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('rating', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('course_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], name=op.f('fk_reviews_course_id_courses')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_reviews_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_reviews')),
    sa.UniqueConstraint('course_id', 'user_id', name='uq_reviews_course_user')
    )


def downgrade():
    op.drop_table('reviews')
