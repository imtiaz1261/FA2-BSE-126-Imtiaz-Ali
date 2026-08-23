"""Create RAG (document Q&A) schema with pgvector support.

Revision ID: 0004
Revises: 0003_settings_and_models
Create Date: 2024-08-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create RAG tables with pgvector support."""
    
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Create uploaded_documents table
    op.create_table(
        "uploaded_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(50),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_uploaded_documents_conversation_id",
        "uploaded_documents",
        ["conversation_id"],
    )
    op.create_index(
        "ix_uploaded_documents_status",
        "uploaded_documents",
        ["status"],
    )
    op.create_index(
        "ix_uploaded_documents_user_id",
        "uploaded_documents",
        ["user_id"],
    )

    # Create document_chunks table
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSON(none_as_null=True),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["uploaded_documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_chunks_document_id",
        "document_chunks",
        ["document_id"],
    )
    op.create_index(
        "ix_document_chunks_page_number",
        "document_chunks",
        ["page_number"],
    )

    # Create document_embeddings table with pgvector
    op.create_table(
        "document_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "embedding",
            Vector(1536),  # text-embedding-3-small is 1536-dim
            nullable=False,
        ),
        sa.Column(
            "embedding_model",
            sa.String(100),
            server_default="text-embedding-3-small",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["document_chunks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["uploaded_documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_embeddings_chunk_id",
        "document_embeddings",
        ["chunk_id"],
    )
    op.create_index(
        "ix_document_embeddings_document_id",
        "document_embeddings",
        ["document_id"],
    )

    # Create upload_jobs table
    op.create_table(
        "upload_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.String(50),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("progress", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["uploaded_documents.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_upload_jobs_document_id",
        "upload_jobs",
        ["document_id"],
    )
    op.create_index(
        "ix_upload_jobs_status",
        "upload_jobs",
        ["status"],
    )
    op.create_index(
        "ix_upload_jobs_user_id",
        "upload_jobs",
        ["user_id"],
    )


def downgrade() -> None:
    """Drop RAG tables."""
    op.drop_index("ix_upload_jobs_user_id", table_name="upload_jobs")
    op.drop_index("ix_upload_jobs_status", table_name="upload_jobs")
    op.drop_index("ix_upload_jobs_document_id", table_name="upload_jobs")
    op.drop_table("upload_jobs")
    
    op.drop_index(
        "ix_document_embeddings_document_id", table_name="document_embeddings"
    )
    op.drop_index(
        "ix_document_embeddings_chunk_id", table_name="document_embeddings"
    )
    op.drop_table("document_embeddings")
    
    op.drop_index(
        "ix_document_chunks_page_number", table_name="document_chunks"
    )
    op.drop_index(
        "ix_document_chunks_document_id", table_name="document_chunks"
    )
    op.drop_table("document_chunks")
    
    op.drop_index(
        "ix_uploaded_documents_user_id",
        table_name="uploaded_documents",
    )
    op.drop_index(
        "ix_uploaded_documents_status",
        table_name="uploaded_documents",
    )
    op.drop_index(
        "ix_uploaded_documents_conversation_id",
        table_name="uploaded_documents",
    )
    op.drop_table("uploaded_documents")
