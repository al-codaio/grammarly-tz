"""State management for the Grammarly support chatbot."""

from typing import TypedDict, List, Optional, Dict, Any, Annotated
from dataclasses import dataclass
from datetime import datetime
import operator


@dataclass
class Message:
    """Represents a conversation message."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class IntentClassification:
    """Results from intent classification."""
    intent: str
    confidence: float
    entities: Dict[str, List[str]]
    urgency: str
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class SupportResponse:
    """Generated support response."""
    content: str
    requires_human: bool = False
    suggested_actions: List[str] = None
    confidence: float = 1.0
    raw_response: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.suggested_actions is None:
            self.suggested_actions = []


class ConversationState(TypedDict):
    """State for the conversation graph."""
    # Core conversation data
    messages: Annotated[List[Message], operator.add]
    current_query: str
    conversation_id: str
    episode_id: str
    
    # Intent classification results
    intent_classification: Optional[IntentClassification]
    
    # Response generation
    generated_response: Optional[SupportResponse]
    
    # Metadata for tracking
    tensorzero_metadata: Dict[str, Any]
    timestamp: datetime
    
    # Control flow
    requires_human: bool
    error_message: Optional[str]
    attempt_count: int
    
    # Context for better responses
    user_context: Dict[str, Any]  # Platform, version, account type, etc.
    knowledge_base_results: Optional[List[Dict[str, Any]]]
    
    # Evaluation data
    response_quality_score: Optional[float]
    resolution_prediction: Optional[bool]


class ErrorState(TypedDict):
    """State for error handling."""
    error_type: str
    error_message: str
    error_context: Dict[str, Any]
    recovery_attempts: int
    timestamp: datetime


def create_initial_state(user_query: str, conversation_id: str = None, episode_id: str = None) -> ConversationState:
    """Create initial conversation state."""
    from uuid import uuid4
    
    return ConversationState(
        messages=[Message(role="user", content=user_query)],
        current_query=user_query,
        conversation_id=conversation_id or str(uuid4()),
        episode_id=episode_id or str(uuid4()),
        intent_classification=None,
        generated_response=None,
        tensorzero_metadata={},
        timestamp=datetime.utcnow(),
        requires_human=False,
        error_message=None,
        attempt_count=0,
        user_context={},
        knowledge_base_results=None,
        response_quality_score=None,
        resolution_prediction=None
    )