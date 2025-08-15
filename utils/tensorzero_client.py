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
        # All variants use the same messages format for JSON functions
        # Note: DICL variants still expect "value" instead of "text"
        content = [{"type": "text", "value": query}]
        request_data = {
            "function_name": "classify_intent",
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": content
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
        
        # All variants use messages format
        # Note: DICL variants still expect "value" instead of "text"
        content = [{"type": "text", "value": formatted_message}]
        request_data = {
            "function_name": "generate_response",
            "episode_id": episode_id,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": content
                    }
                ]
            },
            "stream": False
        }
        
        if variant:
            request_data["variant_name"] = variant
        
        # Debug logging temporarily disabled
        # print(f"Sending generate_response request with variant={variant}:")
        # print(json.dumps(request_data, indent=2))
        
        response = await self.client.post(
            f"{self.base_url}/inference",
            json=request_data
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Check the actual response structure
        if "error" in result:
            raise Exception(f"TensorZero error: {result['error']}")
        
        # Handle JSON function response
        if "output" in result and isinstance(result["output"], dict):
            # Parse the raw JSON output
            if "raw" in result["output"]:
                output_data = json.loads(result["output"]["raw"])
            else:
                output_data = result["output"]
            
            # Extract fields from the JSON response
            return {
                "content": output_data.get("response", ""),
                "requires_human": output_data.get("requires_human", False),
                "suggested_actions": output_data.get("suggested_actions", []),
                "confidence": output_data.get("confidence", 1.0),
                "raw_response": result
            }
        else:
            # Log the actual response for debugging
            print(f"Unexpected response structure: {json.dumps(result, indent=2)}")
            raise Exception(f"Unexpected response structure from TensorZero")
    
    async def send_feedback(
        self,
        inference_id: Optional[str] = None,
        episode_id: Optional[str] = None,
        metric_name: str = None,
        value: Any = None
    ) -> Dict[str, Any]:
        """Send feedback for a specific inference or episode.
        
        For inference-level metrics: provide only inference_id
        For episode-level metrics: provide only episode_id
        """
        if not metric_name or value is None:
            raise ValueError("metric_name and value are required")
            
        request_data = {
            "metric_name": metric_name,
            "value": value
        }
        
        # Add either inference_id OR episode_id, not both
        if inference_id and not episode_id:
            request_data["inference_id"] = inference_id
        elif episode_id and not inference_id:
            request_data["episode_id"] = episode_id
        else:
            raise ValueError("Provide either inference_id OR episode_id, not both or neither")
        
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