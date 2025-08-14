"""Main LangGraph application for Grammarly support chatbot."""

import logging
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Enable LangSmith tracing
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "grammarly-support-chatbot"

from src.state import ConversationState, create_initial_state
from src.nodes import (
    classify_intent_node,
    generate_response_node,
    quality_check_node,
    feedback_node,
    knowledge_retrieval_node,
    human_handoff_node
)


logger = logging.getLogger(__name__)


def should_retrieve_knowledge(state: ConversationState) -> bool:
    """Determine if knowledge retrieval is needed."""
    if not state.get("intent_classification"):
        return False
    
    # Retrieve knowledge for certain intents
    knowledge_intents = ["technical_support", "feature_request", "bug_report", "integration_help"]
    return state["intent_classification"].intent in knowledge_intents


def should_escalate_to_human(state: ConversationState) -> bool:
    """Determine if human escalation is needed."""
    return state.get("requires_human", False)


def should_retry_classification(state: ConversationState) -> bool:
    """Determine if we should retry intent classification."""
    return (
        state.get("error_message") is not None and
        state.get("attempt_count", 0) < 2 and
        not state.get("intent_classification")
    )


def build_graph() -> StateGraph:
    """Build the LangGraph for the support chatbot."""
    
    # Create the graph
    workflow = StateGraph(ConversationState)
    
    # Add nodes
    workflow.add_node("classify_intent", classify_intent_node)
    workflow.add_node("retrieve_knowledge", knowledge_retrieval_node)
    workflow.add_node("generate_response", generate_response_node)
    workflow.add_node("quality_check", quality_check_node)
    workflow.add_node("send_feedback", feedback_node)
    workflow.add_node("human_handoff", human_handoff_node)
    
    # Define the flow
    workflow.set_entry_point("classify_intent")
    
    # From classify_intent
    workflow.add_conditional_edges(
        "classify_intent",
        lambda state: "retry" if should_retry_classification(state) else "continue",
        {
            "retry": "classify_intent",
            "continue": "retrieve_knowledge"
        }
    )
    
    # From retrieve_knowledge
    workflow.add_conditional_edges(
        "retrieve_knowledge",
        lambda state: "retrieve" if should_retrieve_knowledge(state) else "skip",
        {
            "retrieve": "generate_response",
            "skip": "generate_response"
        }
    )
    
    # From generate_response
    workflow.add_edge("generate_response", "quality_check")
    
    # From quality_check
    workflow.add_conditional_edges(
        "quality_check",
        lambda state: "escalate" if should_escalate_to_human(state) else "continue",
        {
            "escalate": "human_handoff",
            "continue": "send_feedback"
        }
    )
    
    # From send_feedback
    workflow.add_edge("send_feedback", END)
    
    # From human_handoff
    workflow.add_edge("human_handoff", "send_feedback")
    
    return workflow


class GrammarlySupportChatBot:
    """Main chatbot application."""
    
    def __init__(self, checkpoint_dir: str = "./checkpoints"):
        """Initialize the chatbot with optional checkpointing."""
        self.graph = build_graph()
        self.checkpointer = MemorySaver()
        self.app = self.graph.compile(checkpointer=self.checkpointer)
    
    async def process_query(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        episode_id: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None,
        variant: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a customer support query."""
        
        # Create initial state
        initial_state = create_initial_state(query, conversation_id, episode_id)
        
        # Add user context if provided
        if user_context:
            initial_state["user_context"] = user_context
        
        # Configuration for the run
        config = {
            "configurable": {
                "thread_id": conversation_id or initial_state["conversation_id"]
            }
        }
        
        # Run the graph
        try:
            final_state = await self.app.ainvoke(initial_state, config)
            
            # Extract the response
            response = {
                "conversation_id": final_state["conversation_id"],
                "episode_id": final_state["episode_id"],
                "response": final_state["generated_response"].content if final_state.get("generated_response") else None,
                "intent": final_state["intent_classification"].intent if final_state.get("intent_classification") else None,
                "requires_human": final_state.get("requires_human", False),
                "quality_score": final_state.get("response_quality_score"),
                "suggested_actions": final_state["generated_response"].suggested_actions if final_state.get("generated_response") else [],
                "knowledge_articles": final_state.get("knowledge_base_results", [])
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "conversation_id": conversation_id,
                "episode_id": episode_id,
                "response": "I apologize, but I'm experiencing technical difficulties. Please contact our support team directly.",
                "intent": None,
                "requires_human": True,
                "quality_score": 0.0,
                "suggested_actions": ["Contact support directly"],
                "knowledge_articles": [],
                "error": str(e)
            }
    
    def visualize(self, output_path: str = "./graph.png"):
        """Visualize the graph structure."""
        try:
            from PIL import Image
            img = Image.open(self.app.get_graph().draw_mermaid_png())
            img.save(output_path)
            logger.info(f"Graph visualization saved to {output_path}")
        except Exception as e:
            logger.error(f"Error visualizing graph: {e}")


# LangGraph Studio entry point
agent = build_graph().compile()


if __name__ == "__main__":
    # Example usage
    import asyncio
    
    async def main():
        bot = GrammarlySupportChatBot()
        
        # Test query
        response = await bot.process_query(
            "I can't get Grammarly to work in Google Docs. It was working yesterday but now it's not showing up.",
            user_context={
                "platform": "chrome",
                "product": "grammarly_premium"
            }
        )
        
        print(f"Response: {response}")
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Run example
    asyncio.run(main())