"""
Worker package for background job processing.

This package contains the RAG ingestion, embedding generation, and AI agent
execution infrastructure that runs in a separate worker process.

Architecture:
- Documents are uploaded to S3
- Events are queued in Redis
- Worker processes pick up events and:
  - Extract text from documents
  - Generate embeddings using OpenAI
  - Store vectors in PostgreSQL + pgvector
  - Execute agent jobs in sandboxed environment

Workers are independently scalable from the API pods.
"""
