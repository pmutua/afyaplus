"""HTTP request and response schemas for the AfyaPlus API."""

from app.models.requests import ChatRequest
from app.models.responses import ChatResponse, HealthResponse

__all__ = ["ChatRequest", "ChatResponse", "HealthResponse"]
