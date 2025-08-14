"""Structured wrapper for TensorZero that preserves input/output validation."""

from typing import Dict, Any, Optional, List
import json
from src.validation import SupportRequestInput, GenerateResponseOutput
from utils.tensorzero_client import TensorZeroClient


class StructuredTensorZeroClient:
    """Wrapper that adds structured validation to TensorZero calls."""
    
    def __init__(self, base_url: str = None):
        self.client = TensorZeroClient(base_url)
    
    async def __aenter__(self):
        await self.client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def generate_response_structured(
        self,
        request: SupportRequestInput,
        episode_id: str,
        variant: Optional[str] = None
    ) -> GenerateResponseOutput:
        """Generate response with structured input/output validation."""
        
        # Convert validated input to dict for the client
        intent_data = None
        if request.intent:
            intent_data = {
                "intent": request.intent,
                "urgency": request.urgency,
                "entities": request.entities,
                "confidence": 1.0  # Since it's manually provided
            }
        
        # Call the underlying client
        response_dict = await self.client.generate_response(
            query=request.query,
            episode_id=episode_id,
            intent_data=intent_data,
            conversation_history=request.conversation_history,
            variant=variant
        )
        
        # Try to extract structured data from the response
        content = response_dict.get("content", "")
        
        # Look for JSON structure in the response (if using json_mode)
        structured_output = None
        try:
            # Check if the content is JSON
            if content.strip().startswith("{"):
                structured_output = json.loads(content)
        except:
            pass
        
        # Build structured output
        if structured_output and isinstance(structured_output, dict):
            # Response is already structured
            output = GenerateResponseOutput(
                response=structured_output.get("response", content),
                confidence=structured_output.get("confidence", 0.8),
                requires_human=structured_output.get("requires_human", False),
                suggested_actions=structured_output.get("suggested_actions", []),
                metadata=structured_output.get("metadata", {})
            )
        else:
            # Parse unstructured response
            requires_human = response_dict.get("requires_human", False)
            suggested_actions = response_dict.get("suggested_actions", [])
            
            output = GenerateResponseOutput(
                response=content,
                confidence=response_dict.get("confidence", 0.8),
                requires_human=requires_human,
                suggested_actions=suggested_actions,
                metadata={
                    "response_type": "unstructured",
                    "raw_response_keys": list(response_dict.keys())
                }
            )
        
        # Store raw response in metadata
        output.metadata["raw_response"] = response_dict.get("raw_response", {})
        
        return output
    
    async def classify_intent(self, *args, **kwargs):
        """Delegate to underlying client."""
        return await self.client.classify_intent(*args, **kwargs)
    
    async def send_feedback(self, *args, **kwargs):
        """Delegate to underlying client."""
        return await self.client.send_feedback(*args, **kwargs)
    
    async def health_check(self):
        """Delegate to underlying client."""
        return await self.client.health_check()