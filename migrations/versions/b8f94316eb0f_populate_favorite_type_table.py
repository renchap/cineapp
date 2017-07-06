"""Populate favorite_type table

Revision ID: b8f94316eb0f
Revises: bbda659bcd01
Create Date: 2017-07-06 23:23:38.163554

"""

# revision identifiers, used by Alembic.
revision = 'b8f94316eb0f'
down_revision = 'bbda659bcd01'

from alembic import op
import sqlalchemy as sa
import cineapp.migration_types

def upgrade():
    fav_table = cineapp.models.FavoriteType.__table__
    op.bulk_insert(fav_table,
    [
        {'star_type':"favorite_star", 'star_message':'Favori'},
        {'star_type':"homework_star", 'star_message':'A donner en devoir'},
        {'star_type':"mustsee_star", 'star_message':'A voir absolument'},
    ]
)

def downgrade():
    pass
