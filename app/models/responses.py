"""Response schemas for the AfyaPlus API."""

from pydantic import BaseModel


class ChatResponse(BaseModel):
    """Final de-masked response for one conversation session."""

    response: str
    thread_id: str


class HealthResponse(BaseModel):
    """Lightweight process health response."""

    status: str
