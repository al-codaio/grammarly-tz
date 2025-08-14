"""TensorZero client for interacting with the gateway."""

import os
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

# Import moved to avoid circular dependency


class TensorZeroClient:
    """Client for interacting with TensorZero gateway."""
    
    def __init__(self, base_url: str = None, timeout: float = 30.0):
        self.base_url = base_url or os.getenv("TENSORZERO_GATEWAY_URL", "http://localhost:3000")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def classify_intent(
        self,
        query: str,
        episode_id: str,
        conversation_id: Optional[str] = None,
        variant: Optional[str] = None
    ) -> Dict[str, Any]:
        """Classify customer intent using TensorZero."""
        request_data = {
            "function_name": "classify_intent",
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": query}]
                    }
                ]
            }
        }
        
        if episode_id:
            request_data["episode_id"] = episode_id
        
        if variant:
            request_data["variant_name"] = variant
        
        response = await self.client.post(
            f"{self.base_url}/inference",
            json=request_data
        )
        response.raise_for_status()
        
        result = response.json()
        output = json.loads(result["output"]["raw"])
        
        # Return a dict instead of IntentClassification to avoid circular import
        return {
            "intent": output["intent"],
            "confidence": output["confidence"],
            "entities": output["entities"],
            "urgency": output["urgency"],
            "raw_response": result
        }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def generate_response(
        self,
        query: str,
        episode_id: str,
        intent_data: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        variant: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate support response using TensorZero."""
        
        # Build a formatted message with all context since we can't use template variables
        message_parts = [f"Customer Query: {query}"]
        
        if intent_data:
            message_parts.append(f"\nClassified Intent: {intent_data['intent']}")
            message_parts.append(f"Urgency Level: {intent_data['urgency']}")
            
            if intent_data.get('entities'):
                message_parts.append("\nContext Information:")
                entities = intent_data['entities']
                if entities.get("product"):
                    message_parts.append(f"  - Products: {', '.join(entities['product'])}")
                if entities.get("feature"):
                    message_parts.append(f"  - Features: {', '.join(entities['feature'])}")
                if entities.get("platform"):
                    message_parts.append(f"  - Platform: {', '.join(entities['platform'])}")
                if entities.get("error_code"):
                    message_parts.append(f"  - Error Codes: {', '.join(entities['error_code'])}")
        
        if conversation_history:
            message_parts.append("\nPrevious Conversation:")
            for msg in conversation_history:
                message_parts.append(f"{msg['role'].capitalize()}: {msg['content']}")
        
        message_parts.append("\nPlease provide a helpful and comprehensive response to address the customer's concern. Include specific steps or solutions when applicable.")
        
        formatted_message = "\n".join(message_parts)
        
        # Construct the request - TensorZero expects messages format
        request_data = {
            "function_name": "generate_response",
            "episode_id": episode_id,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": formatted_message}]
                    }
                ]
            },
            "stream": False
        }
        
        if variant:
            request_data["variant_name"] = variant
        
        response = await self.client.post(
            f"{self.base_url}/inference",
            json=request_data
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Check the actual response structure
        if "error" in result:
            raise Exception(f"TensorZero error: {result['error']}")
        
        # Try different possible response structures
        if "output" in result and isinstance(result["output"], dict):
            content = result["output"].get("content", result["output"].get("raw", ""))
        elif "content" in result:
            content = result["content"]
        else:
            # Log the actual response for debugging
            print(f"Unexpected response structure: {json.dumps(result, indent=2)}")
            raise Exception(f"Unexpected response structure from TensorZero")
        
        # Handle content as list (chat response format)
        if isinstance(content, list):
            # Extract text from content blocks
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    # Try both 'text' and 'value' keys
                    text_parts.append(block.get("text", block.get("value", "")))
                elif isinstance(block, str):
                    text_parts.append(block)
            content = "\n".join(text_parts)
        
        # Parse response for special markers
        requires_human = "[ESCALATE]" in content
        content = content.replace("[ESCALATE]", "").strip()
        
        # Extract suggested actions if present
        suggested_actions = []
        if "[ACTIONS]" in content:
            parts = content.split("[ACTIONS]")
            content = parts[0].strip()
            if len(parts) > 1:
                action_text = parts[1].strip()
                suggested_actions = [a.strip() for a in action_text.split("\n") if a.strip()]
        
        # Return a dict instead of SupportResponse to avoid circular import
        return {
            "content": content,
            "requires_human": requires_human,
            "suggested_actions": suggested_actions,
            "confidence": result.get("metadata", {}).get("confidence", 1.0),
            "raw_response": result
        }
    
    async def send_feedback(
        self,
        inference_id: str,
        metric_name: str,
        value: Any,
        episode_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send feedback for a specific inference."""
        request_data = {
            "inference_id": inference_id,
            "metric_name": metric_name,
            "value": value
        }
        
        if episode_id:
            request_data["episode_id"] = episode_id
        
        response = await self.client.post(
            f"{self.base_url}/feedback",
            json=request_data
        )
        response.raise_for_status()
        
        return response.json()
    
    async def send_demonstration(
        self,
        inference_id: str,
        output: str,
        episode_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a demonstration for a specific inference."""
        request_data = {
            "inference_id": inference_id,
            "value": output
        }
        
        if episode_id:
            request_data["episode_id"] = episode_id
        
        response = await self.client.post(
            f"{self.base_url}/feedback",
            json=request_data
        )
        response.raise_for_status()
        
        return response.json()
    
    async def health_check(self) -> bool:
        """Check if TensorZero gateway is healthy."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False