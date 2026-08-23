"""Schemas for settings and models endpoints."""

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SettingsPreferences(BaseModel):
    """User preference settings stored as JSON."""

    theme: str = Field(default="system", description="Theme: light, dark, or system")
    font_size: str = Field(default="medium", description="Font size: small, medium, or large")
    language: str = Field(default="en", description="Language code: en, es, fr, de, ja, zh")
    assistant_context: str = Field(
        default="", description="Context about the user for the assistant to know"
    )
    response_preferences: str = Field(
        default="", description="Preferences for how the assistant should respond"
    )


class SettingsResponse(BaseModel):
    """User settings response."""

    preferences: SettingsPreferences

    class Config:
        from_attributes = True


class SettingsPatchRequest(BaseModel):
    """Request to update user settings."""

    preferences: Optional[SettingsPreferences] = None


class AvailableModelResponse(BaseModel):
    """Available LLM model."""

    id: str
    name: str
    display_name: str
    description: str
    tier: str

    class Config:
        from_attributes = True


class ModelSelectorResponse(BaseModel):
    """Model selector for conversation."""

    conversation_id: str
    selected_model_id: Optional[str] = None
    selected_model: Optional[AvailableModelResponse] = None
    available_models: list[AvailableModelResponse]


class ModelSelectionRequest(BaseModel):
    """Request to select a model for a conversation."""

    model_config = ConfigDict(protected_namespaces=())

    model_id: str


class UsageResponse(BaseModel):
    """Daily message usage for the current user."""

    used: int = Field(description="Messages used today")
    limit: int = Field(description="Daily limit for free tier")
    remaining: int = Field(description="Messages remaining today")


class ExportJobResponse(BaseModel):
    """Status of an async data export job."""

    job_id: str
    status: str  # pending, processing, completed, failed
    download_url: Optional[str] = None
    expires_at: Optional[str] = None


class ExportJobRequest(BaseModel):
    """Request to initiate data export."""

    pass


class ClearConversationsRequest(BaseModel):
    """Request to clear all conversations."""

    confirmation: str = Field(description="User must type 'I understand' to confirm")


class DeleteAccountRequest(BaseModel):
    """Request to delete account."""

    confirmation: str = Field(
        description="User must type their email or 'I understand' to confirm"
    )
    password: Optional[str] = Field(default=None, description="Password for additional verification")
