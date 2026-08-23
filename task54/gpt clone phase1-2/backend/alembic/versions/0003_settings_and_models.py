"""Add settings, models, and usage tracking tables.

Revision ID: 0003_settings_and_models
Revises: 0002_conversation_history
Create Date: 2024-08-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0003_settings_and_models'
down_revision = '0002_conversation_history'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_settings table
    op.create_table(
        'user_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('preferences', postgresql.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index('ix_user_settings_user_id', 'user_settings', ['user_id'])

    # Create available_models table
    op.create_table(
        'available_models',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('display_name', sa.String(120), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('tier', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index('ix_available_models_name', 'available_models', ['name'])
    op.create_index('ix_available_models_tier', 'available_models', ['tier'])

    # Create conversation_models table
    op.create_table(
        'conversation_models',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['model_id'], ['available_models.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_conversation_models_conversation_id', 'conversation_models', ['conversation_id'])
    op.create_index('ix_conversation_models_model_id', 'conversation_models', ['model_id'])

    # Create message_usage table
    op.create_table(
        'message_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_message_usage_user_date', 'message_usage', ['user_id', 'date'])
    op.create_index('ix_message_usage_user_id', 'message_usage', ['user_id'])

    # Create data_export_jobs table
    op.create_table(
        'data_export_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('download_url', sa.String(255), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_data_export_jobs_user_id', 'data_export_jobs', ['user_id'])

    # Seed initial models
    op.execute("""
    INSERT INTO available_models (id, name, display_name, description, tier, is_active)
    VALUES 
        (gen_random_uuid(), 'gpt-4-fast', 'Fast', 'Quick responses, ideal for simple tasks and brainstorming', 'fast', true),
        (gen_random_uuid(), 'gpt-4-balanced', 'Balanced', 'Balanced speed and reasoning, suitable for most tasks', 'balanced', true),
        (gen_random_uuid(), 'gpt-4-advanced', 'Advanced Reasoning', 'Deep reasoning for complex analysis and problem-solving', 'advanced-reasoning', true)
    ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_table('data_export_jobs')
    op.drop_table('message_usage')
    op.drop_table('conversation_models')
    op.drop_table('available_models')
    op.drop_table('user_settings')
