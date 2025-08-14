"""Input validation for structured data."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator


class SupportRequestInput(BaseModel):
    """Validated support request input."""
    
    query: str = Field(..., min_length=1, description="The customer's query")
    intent: Optional[str] = Field(None, description="Classified intent")
    urgency: Optional[str] = Field("medium", description="Urgency level")
    entities: Optional[Dict[str, List[str]]] = Field(default_factory=dict)
    conversation_history: Optional[List[Dict[str, str]]] = Field(default_factory=list)
    
    @validator('urgency')
    def validate_urgency(cls, v):
        """Ensure urgency is valid."""
        if v and v not in ['low', 'medium', 'high', 'critical']:
            raise ValueError(f'Invalid urgency level: {v}')
        return v
    
    @validator('conversation_history')
    def validate_conversation_history(cls, v):
        """Ensure conversation history has proper structure."""
        if v:
            for msg in v:
                if 'role' not in msg or 'content' not in msg:
                    raise ValueError('Each message must have role and content')
                if msg['role'] not in ['user', 'assistant', 'system']:
                    raise ValueError(f'Invalid role: {msg["role"]}')
        return v


class GenerateResponseOutput(BaseModel):
    """Structured output from generate_response."""
    
    response: str = Field(..., description="The response to the customer")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")
    requires_human: bool = Field(False, description="Whether human intervention is needed")
    suggested_actions: List[str] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


def validate_support_request(data: Dict[str, Any]) -> SupportRequestInput:
    """Validate and return structured support request input."""
    return SupportRequestInput(**data)