"""Initial database schema.

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000

Alembic is the single source of truth for schema management.
Apply this migration with `alembic upgrade head` before starting the bot.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.Text(), nullable=True),
        sa.Column('virtual_balance', sa.Numeric(), server_default='10000.0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id')
    )
    op.create_index('idx_users_telegram_id', 'users', ['telegram_id'])

    # Create matches table
    op.create_table(
        'matches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('home_team', sa.Text(), nullable=False),
        sa.Column('away_team', sa.Text(), nullable=False),
        sa.Column('league', sa.Text(), nullable=True),
        sa.Column('match_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.Text(), server_default='scheduled'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_matches_date', 'matches', ['match_date'])

    # Create predictions table
    op.create_table(
        'predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('match_id', sa.Integer(), nullable=True),
        sa.Column('outcome', sa.Text(), nullable=True),
        sa.Column('probability', sa.Numeric(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_predictions_match', 'predictions', ['match_id'])

    # Create virtual_bets table
    op.create_table(
        'virtual_bets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('match_id', sa.Integer(), nullable=True),
        sa.Column('outcome', sa.Text(), nullable=True),
        sa.Column('amount', sa.Numeric(), nullable=True),
        sa.Column('odds', sa.Numeric(), nullable=True),
        sa.Column('result', sa.Text(), server_default='pending'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_bets_user', 'virtual_bets', ['user_id'])


def downgrade() -> None:
    op.drop_index('idx_bets_user', table_name='virtual_bets')
    op.drop_table('virtual_bets')
    
    op.drop_index('idx_predictions_match', table_name='predictions')
    op.drop_table('predictions')
    
    op.drop_index('idx_matches_date', table_name='matches')
    op.drop_table('matches')
    
    op.drop_index('idx_users_telegram_id', table_name='users')
    op.drop_table('users')
