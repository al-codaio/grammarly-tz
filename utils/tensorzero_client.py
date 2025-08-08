"""TensorZero client for interacting with the gateway."""

import os
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.state import IntentClassification, SupportResponse


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
    ) -> IntentClassification:
        """Classify customer intent using TensorZero."""
        request_data = {
            "function_name": "classify_intent",
            "episode_id": episode_id,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "value": query}]
                    }
                ]
            }
        }
        
        if variant:
            request_data["variant_name"] = variant
        
        response = await self.client.post(
            f"{self.base_url}/inference",
            json=request_data
        )
        response.raise_for_status()
        
        result = response.json()
        output = json.loads(result["output"]["raw"])
        
        return IntentClassification(
            intent=output["intent"],
            confidence=output["confidence"],
            entities=output["entities"],
            urgency=output["urgency"],
            raw_response=result
        )
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def generate_response(
        self,
        query: str,
        episode_id: str,
        intent_data: Optional[IntentClassification] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        variant: Optional[str] = None
    ) -> SupportResponse:
        """Generate support response using TensorZero."""
        # Build the user message with template variables
        template_inputs = {
            "query": query,
            "intent": intent_data.intent if intent_data else None,
            "urgency": intent_data.urgency if intent_data else None,
            "entities": intent_data.entities if intent_data else {},
            "conversation_history": conversation_history or []
        }
        
        request_data = {
            "function_name": "generate_response",
            "episode_id": episode_id,
            "input": template_inputs,
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
        content = result["output"]["content"]
        
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
        
        return SupportResponse(
            content=content,
            requires_human=requires_human,
            suggested_actions=suggested_actions,
            confidence=result.get("metadata", {}).get("confidence", 1.0),
            raw_response=result
        )
    
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