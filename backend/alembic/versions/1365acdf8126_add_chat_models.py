"""add chat models

Revision ID: 1365acdf8126
Revises: 0003
Create Date: 2026-07-09 08:29:25.459275
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1365acdf8126'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('chat_threads',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('trial_id', sa.UUID(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['trial_id'], ['trials.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_threads_trial_id'), 'chat_threads', ['trial_id'], unique=False)
    op.create_table('chat_messages',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('thread_id', sa.UUID(), nullable=False),
    sa.Column('role', sa.String(length=50), nullable=False),
    sa.Column('content', sa.String(), nullable=False),
    sa.Column('grounding_failure', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['thread_id'], ['chat_threads.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_messages_thread_id'), 'chat_messages', ['thread_id'], unique=False)
    op.create_table('message_citations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('message_id', sa.UUID(), nullable=False),
    sa.Column('chunk_id', sa.UUID(), nullable=False),
    sa.Column('citation_index', sa.Integer(), nullable=False),
    sa.Column('document_id', sa.UUID(), nullable=False),
    sa.Column('content_excerpt', sa.String(), nullable=True),
    sa.Column('page_number', sa.Integer(), nullable=True),
    sa.Column('relevance_score', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_message_citations_message_id'), 'message_citations', ['message_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_message_citations_message_id'), table_name='message_citations')
    op.drop_table('message_citations')
    op.drop_index(op.f('ix_chat_messages_thread_id'), table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_index(op.f('ix_chat_threads_trial_id'), table_name='chat_threads')
    op.drop_table('chat_threads')
