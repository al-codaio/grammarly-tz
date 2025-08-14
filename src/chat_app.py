"""Simple chat interface for LangGraph Studio."""

from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
import logging
import os

# Load environment variables
load_dotenv()

# Enable LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "grammarly-support-chatbot"

# Debug: Print to verify env vars are loaded
if os.getenv("LANGSMITH_API_KEY"):
    print("✓ LangSmith API key loaded successfully")
else:
    print("✗ WARNING: LangSmith API key not found")

from src.app import build_graph, GrammarlySupportChatBot
from src.state import create_initial_state

logger = logging.getLogger(__name__)


# Simple state for chat interface
from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage

class ChatState(TypedDict):
    """Simple state that works with LangGraph Studio chat interface."""
    messages: Annotated[Sequence[BaseMessage], operator.add]


async def chat_node(state: ChatState) -> Dict[str, Any]:
    """Process chat message through the main graph."""
    # Extract the user message from chat format
    messages = state.get("messages", [])
    if not messages:
        from langchain_core.messages import AIMessage
        return {"messages": [AIMessage(content="Please provide a message.")]}
    
    # Get the latest user message
    user_message = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
    
    # Create the bot and process the query
    bot = GrammarlySupportChatBot()
    result = await bot.process_query(
        query=user_message,
        conversation_id=state.get("conversation_id"),
        episode_id=state.get("episode_id")
    )
    
    # Format the response for chat
    response_content = result.get("response", "I apologize, but I couldn't process your request.")
    
    # Add metadata to the response
    if result.get("intent"):
        response_content += f"\n\n---\n📊 Intent: {result['intent']}"
    if result.get("requires_human"):
        response_content += "\n⚠️ Human escalation recommended"
    if result.get("quality_score") is not None:
        response_content += f"\n💯 Quality: {result['quality_score']:.0%}"
    
    from langchain_core.messages import AIMessage
    return {
        "messages": [AIMessage(content=response_content)]
    }


# Build simple chat graph
def build_chat_graph():
    """Build a simple graph for chat interface."""
    workflow = StateGraph(ChatState)
    
    # Single node that processes everything
    workflow.add_node("chat", chat_node)
    
    # Simple flow
    workflow.set_entry_point("chat")
    workflow.add_edge("chat", END)
    
    return workflow.compile()


# LangGraph Studio entry point - this enables chat interface
chat_agent = build_chat_graph()