"""Validated request schemas for the AfyaPlus API."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_PATIENT_MESSAGE = "I need to confirm the maternity coverage waiting period."


class ChatRequest(BaseModel):
    """One chat turn and the non-PII session identifier that owns its memory."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "message": DEFAULT_PATIENT_MESSAGE,
                    "thread_id": "demo-session-001",
                }
            ]
        }
    )

    message: str = Field(min_length=1, max_length=8_000)
    thread_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$",
    )

    @field_validator("message", "thread_id", mode="before")
    @classmethod
    def strip_text_fields(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value
