"""Pydantic request/response schemas."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message to send to the LLM")

    @field_validator("message")
    @classmethod
    def _strip_and_check(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message cannot be empty")
        return v


class ChatResponse(BaseModel):
    response: str
    model: str
    provider: str


class RootResponse(BaseModel):
    application: str
    version: str
    status: str


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    llm_configured: bool


class ErrorResponse(BaseModel):
    error: str
