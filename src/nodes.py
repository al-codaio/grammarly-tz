"""LangGraph nodes for the Grammarly support chatbot."""

import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime

from src.state import ConversationState, Message, IntentClassification, SupportResponse
from utils.tensorzero_client import TensorZeroClient


logger = logging.getLogger(__name__)


async def classify_intent_node(state: ConversationState) -> Dict[str, Any]:
    """Classify the intent of the current query."""
    logger.info(f"Classifying intent for query: {state['current_query'][:50]}...")
    
    try:
        async with TensorZeroClient() as client:
            # Use the variant based on attempt count for fallback
            variant = None
            if state["attempt_count"] > 0:
                variant = "gpt_4o"  # Fallback to more powerful model
            
            classification = await client.classify_intent(
                query=state["current_query"],
                episode_id=state["episode_id"],
                conversation_id=state["conversation_id"],
                variant=variant
            )
            
            # Store TensorZero metadata
            tz_metadata = state.get("tensorzero_metadata", {})
            tz_metadata["classify_intent_inference_id"] = classification.raw_response.get("inference_id")
            
            logger.info(f"Intent classified as: {classification.intent} (confidence: {classification.confidence})")
            
            return {
                "intent_classification": classification,
                "tensorzero_metadata": tz_metadata,
                "attempt_count": state["attempt_count"] + 1
            }
    
    except Exception as e:
        logger.error(f"Error classifying intent: {e}")
        return {
            "error_message": f"Failed to classify intent: {str(e)}",
            "attempt_count": state["attempt_count"] + 1,
            "requires_human": state["attempt_count"] >= 2  # Escalate after 2 failed attempts
        }


async def generate_response_node(state: ConversationState) -> Dict[str, Any]:
    """Generate a response to the customer query."""
    logger.info(f"Generating response for intent: {state['intent_classification'].intent if state['intent_classification'] else 'unknown'}")
    
    try:
        async with TensorZeroClient() as client:
            # Prepare conversation history
            conversation_history = []
            for msg in state["messages"][:-1]:  # Exclude current message
                conversation_history.append(msg.to_dict())
            
            # Use variant based on urgency and attempt count
            variant = None
            if state["intent_classification"] and state["intent_classification"].urgency == "critical":
                variant = "gpt_4o"  # Use best model for critical issues
            elif state["attempt_count"] > 1:
                variant = "gpt_4o"  # Fallback to better model
            
            response = await client.generate_response(
                query=state["current_query"],
                episode_id=state["episode_id"],
                intent_data=state["intent_classification"],
                conversation_history=conversation_history,
                variant=variant
            )
            
            # Store TensorZero metadata
            tz_metadata = state.get("tensorzero_metadata", {})
            tz_metadata["generate_response_inference_id"] = response.raw_response.get("inference_id")
            
            # Add assistant message to conversation
            new_message = Message(role="assistant", content=response.content)
            
            logger.info(f"Response generated (requires_human: {response.requires_human})")
            
            return {
                "generated_response": response,
                "messages": [new_message],
                "tensorzero_metadata": tz_metadata,
                "requires_human": response.requires_human
            }
    
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        fallback_response = SupportResponse(
            content="I apologize, but I'm having trouble processing your request. Let me connect you with a human support specialist who can better assist you.",
            requires_human=True,
            confidence=0.0
        )
        
        new_message = Message(role="assistant", content=fallback_response.content)
        
        return {
            "generated_response": fallback_response,
            "messages": [new_message],
            "error_message": f"Failed to generate response: {str(e)}",
            "requires_human": True
        }


async def quality_check_node(state: ConversationState) -> Dict[str, Any]:
    """Check the quality of the generated response."""
    logger.info("Performing quality check on generated response")
    
    if not state["generated_response"]:
        return {"response_quality_score": 0.0, "requires_human": True}
    
    response = state["generated_response"]
    
    # Simple heuristic-based quality checks
    quality_score = 1.0
    issues = []
    
    # Check response length
    if len(response.content) < 50:
        quality_score -= 0.3
        issues.append("Response too short")
    elif len(response.content) > 1000:
        quality_score -= 0.2
        issues.append("Response too long")
    
    # Check for placeholder text
    placeholder_patterns = ["[", "]", "TODO", "FIXME", "{{", "}}"]
    if any(pattern in response.content for pattern in placeholder_patterns):
        quality_score -= 0.5
        issues.append("Contains placeholder text")
    
    # Check confidence from model
    if response.confidence < 0.7:
        quality_score -= 0.3
        issues.append(f"Low confidence: {response.confidence}")
    
    # Check if intent was classified
    if not state["intent_classification"] or state["intent_classification"].confidence < 0.8:
        quality_score -= 0.2
        issues.append("Uncertain intent classification")
    
    quality_score = max(0.0, quality_score)
    
    # Decide if human escalation is needed
    requires_human = (
        quality_score < 0.5 or
        response.requires_human or
        state.get("requires_human", False)
    )
    
    if issues:
        logger.warning(f"Quality issues detected: {', '.join(issues)}")
    
    return {
        "response_quality_score": quality_score,
        "requires_human": requires_human
    }


async def feedback_node(state: ConversationState) -> Dict[str, Any]:
    """Send feedback to TensorZero based on quality checks."""
    logger.info("Sending feedback to TensorZero")
    
    try:
        async with TensorZeroClient() as client:
            tasks = []
            
            # Send intent accuracy feedback if we have classification
            if state["intent_classification"] and "classify_intent_inference_id" in state.get("tensorzero_metadata", {}):
                inference_id = state["tensorzero_metadata"]["classify_intent_inference_id"]
                # For demo purposes, assume intent is correct if confidence > 0.8
                intent_accurate = state["intent_classification"].confidence > 0.8
                
                tasks.append(
                    client.send_feedback(
                        inference_id=inference_id,
                        metric_name="intent_accuracy",
                        value=intent_accurate,
                        episode_id=state["episode_id"]
                    )
                )
            
            # Send response relevance feedback
            if state["generated_response"] and "generate_response_inference_id" in state.get("tensorzero_metadata", {}):
                inference_id = state["tensorzero_metadata"]["generate_response_inference_id"]
                
                tasks.append(
                    client.send_feedback(
                        inference_id=inference_id,
                        metric_name="response_relevance",
                        value=state.get("response_quality_score", 0.5),
                        episode_id=state["episode_id"]
                    )
                )
            
            # Send episode-level feedback
            if not state["requires_human"]:
                tasks.append(
                    client.send_feedback(
                        inference_id=state["episode_id"],
                        metric_name="resolution_potential",
                        value=True,
                        episode_id=state["episode_id"]
                    )
                )
            
            # Execute all feedback tasks
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                logger.info(f"Sent {len(tasks)} feedback items to TensorZero")
    
    except Exception as e:
        logger.error(f"Error sending feedback: {e}")
    
    return {}


async def knowledge_retrieval_node(state: ConversationState) -> Dict[str, Any]:
    """Retrieve relevant knowledge base articles (simulated)."""
    logger.info("Retrieving knowledge base articles")
    
    # In production, this would query actual knowledge base
    # For now, return simulated results based on intent
    
    knowledge_results = []
    
    if state["intent_classification"]:
        intent = state["intent_classification"].intent
        entities = state["intent_classification"].entities
        
        # Simulate knowledge base results
        if intent == "technical_support":
            knowledge_results.append({
                "title": "Troubleshooting Grammarly Browser Extension",
                "url": "https://support.grammarly.com/hc/en-us/articles/360074683451",
                "relevance": 0.9
            })
        elif intent == "billing_inquiry":
            knowledge_results.append({
                "title": "Managing Your Grammarly Subscription",
                "url": "https://support.grammarly.com/hc/en-us/articles/360074683471",
                "relevance": 0.85
            })
        
        # Add product-specific articles
        if "grammarly_business" in entities.get("product", []):
            knowledge_results.append({
                "title": "Grammarly Business Admin Guide",
                "url": "https://support.grammarly.com/hc/en-us/sections/360007930512",
                "relevance": 0.8
            })
    
    return {
        "knowledge_base_results": knowledge_results if knowledge_results else None
    }


async def human_handoff_node(state: ConversationState) -> Dict[str, Any]:
    """Prepare state for human handoff."""
    logger.info("Preparing for human handoff")
    
    handoff_message = Message(
        role="assistant",
        content=(
            "I'll connect you with a human support specialist who can better assist you. "
            "They'll have access to our conversation history and will help resolve your issue. "
            "Please wait a moment while I transfer you."
        )
    )
    
    # Prepare handoff context
    handoff_context = {
        "conversation_id": state["conversation_id"],
        "episode_id": state["episode_id"],
        "intent": state["intent_classification"].intent if state["intent_classification"] else "unknown",
        "urgency": state["intent_classification"].urgency if state["intent_classification"] else "medium",
        "quality_score": state.get("response_quality_score", 0.0),
        "reason": state.get("error_message", "Quality threshold not met"),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return {
        "messages": [handoff_message],
        "tensorzero_metadata": {
            **state.get("tensorzero_metadata", {}),
            "handoff_context": handoff_context
        }
    }