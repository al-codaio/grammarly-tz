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
        # Use the newer "text" format which works with both DICL and non-DICL variants
        # TensorZero will handle the conversion for DICL variants
        content = [{"type": "text", "text": query}]
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
        
        # Simple cleaning - just normalize whitespace
        query = ' '.join(query.split())
        
        # Build a formatted message with all context
        message_parts = []
        message_parts.append(f"Customer Query: {query}")
        
        if intent_data:
            # Clean intent data values too
            intent = intent_data.get('intent', '').replace('\n', ' ').replace('\r', ' ')
            urgency = intent_data.get('urgency', '').replace('\n', ' ').replace('\r', ' ')
            message_parts.append(f"Classified Intent: {intent}")
            message_parts.append(f"Urgency Level: {urgency}")
            
            if intent_data.get('entities'):
                message_parts.append("Context Information:")
                entities = intent_data['entities']
                if entities.get("product"):
                    products = [p.replace('\n', ' ').replace('\r', ' ') for p in entities['product']]
                    message_parts.append(f"Products: {', '.join(products)}")
                if entities.get("feature"):
                    features = [f.replace('\n', ' ').replace('\r', ' ') for f in entities['feature']]
                    message_parts.append(f"Features: {', '.join(features)}")
                if entities.get("platform"):
                    platforms = [p.replace('\n', ' ').replace('\r', ' ') for p in entities['platform']]
                    message_parts.append(f"Platform: {', '.join(platforms)}")
                if entities.get("error_code"):
                    codes = [c.replace('\n', ' ').replace('\r', ' ') for c in entities['error_code']]
                    message_parts.append(f"Error Codes: {', '.join(codes)}")
        
        if conversation_history:
            message_parts.append("Previous Conversation:")
            for msg in conversation_history:
                role = msg['role'].capitalize()
                content = ' '.join(msg['content'].split())  # Clean content too
                message_parts.append(f"{role}: {content}")
        
        message_parts.append("Please provide a helpful and comprehensive response to address the customer's concern. Include specific steps or solutions when applicable.")
        
        # Join with spaces, not newlines, to avoid control character issues
        formatted_message = ' '.join(message_parts)
        
        # Use the newer "text" format which works with both DICL and non-DICL variants
        # TensorZero will handle the conversion for DICL variants
        content = [{"type": "text", "text": formatted_message}]
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
        
        # Handle the new response format with content field (DICL variants return this)
        if "content" in result and isinstance(result["content"], list):
            # Extract text from content blocks
            text_content = ""
            for block in result["content"]:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_content = block.get("text", "")
                    break
            
            # Try to parse as JSON if it looks like JSON
            try:
                if text_content.strip().startswith('{'):
                    output_data = json.loads(text_content)
                    return {
                        "content": output_data.get("response", text_content),
                        "requires_human": output_data.get("requires_human", False),
                        "suggested_actions": output_data.get("suggested_actions", []),
                        "confidence": output_data.get("confidence", 1.0),
                        "raw_response": result
                    }
            except:
                pass
            
            # For non-JSON chat completions, return the text directly
            return {
                "content": text_content,
                "requires_human": False,  # Default to false
                "suggested_actions": [],
                "confidence": 1.0,  # Default confidence
                "raw_response": result
            }
        # Handle JSON function response (for JSON output functions)
        elif "output" in result and isinstance(result["output"], dict):
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