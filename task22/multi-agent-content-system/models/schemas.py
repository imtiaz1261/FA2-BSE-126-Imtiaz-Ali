"""models/schemas.py — Structured data models for every piece of content
that flows between agents.

Using Pydantic models (rather than plain dicts) here means every agent's
input and output shape is validated automatically — if the Researcher
agent ever produced a malformed ResearchSummary, this would fail loudly
right there, instead of silently corrupting the Writer agent's prompt
several steps later.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ContentType(str, Enum):
    """The kinds of content the system can produce. Used to select
    content-type-specific prompt instructions and export formatting."""

    BLOG = "blog"
    ARTICLE = "article"
    REPORT = "report"
    ESSAY = "essay"
    TECHNICAL_DOCUMENTATION = "technical_documentation"


class ExportFormat(str, Enum):
    """Supported output formats for the final content (used by the
    export tool, added in a later step)."""

    MARKDOWN = "markdown"
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class ContentRequest(BaseModel):
    """The user's original request — the input that kicks off the whole
    pipeline."""

    topic: str = Field(..., min_length=3, description="The topic or writing prompt")
    content_type: ContentType = ContentType.ARTICLE
    tone: str = Field(default="professional", min_length=2)
    audience: str = Field(default="general audience", min_length=2)
    word_count: int = Field(default=800, ge=100, le=10000)

    @field_validator("topic")
    @classmethod
    def topic_must_not_be_blank(cls, value: str) -> str:
        """Catches whitespace-only topics, which min_length alone
        wouldn't reject (e.g. '   ' has length 3 but is meaningless)."""
        if not value.strip():
            raise ValueError("Topic cannot be blank or whitespace-only.")
        return value.strip()


class SourceReference(BaseModel):
    """A single web source the Researcher agent found — kept as a
    structured object (not just a URL string) so it can carry a title
    and snippet too, needed for the "source citations" bonus feature."""

    title: str
    url: str
    snippet: str = ""


class ResearchFinding(BaseModel):
    """One discrete fact or statistic the Researcher agent extracted,
    optionally linked back to the source it came from."""

    fact: str
    source: SourceReference | None = None


class ResearchSummary(BaseModel):
    """The Researcher agent's complete output — everything the Writer
    agent needs to produce an informed first draft."""

    topic: str
    research_questions: list[str] = Field(default_factory=list)
    key_findings: list[ResearchFinding] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)

    def to_context_text(self) -> str:
        """Formats this research summary into plain text suitable for
        inserting into the Writer agent's prompt.

        Keeping this formatting logic ON the model itself (rather than
        scattered in the agent's prompt-building code) means there's one
        single place that defines "what research context looks like to
        the LLM" — reused identically by every agent that needs it.
        """
        lines = ["Research questions explored:"]
        for question in self.research_questions:
            lines.append(f"- {question}")

        lines.append("\nKey findings:")
        for finding in self.key_findings:
            source_note = f" (Source: {finding.source.title})" if finding.source else ""
            lines.append(f"- {finding.fact}{source_note}")

        return "\n".join(lines)


class Draft(BaseModel):
    """The Writer agent's output — a complete first draft."""

    title: str
    content: str
    word_count: int = Field(default=0, validate_default=True)

    @field_validator("word_count")
    @classmethod
    def compute_word_count_if_zero(cls, value: int, info) -> int:
        """If word_count wasn't explicitly provided, derive it from the
        content automatically — avoids the Writer agent having to count
        words itself and risk getting it wrong."""
        if value == 0 and "content" in info.data:
            return len(info.data["content"].split())
        return value


class FinalContent(BaseModel):
    """The Editor agent's output — the publication-ready final version."""

    title: str
    content: str
    word_count: int = Field(default=0, validate_default=True)
    edit_notes: list[str] = Field(default_factory=list)

    @field_validator("word_count")
    @classmethod
    def compute_word_count_if_zero(cls, value: int, info) -> int:
        if value == 0 and "content" in info.data:
            return len(info.data["content"].split())
        return value
