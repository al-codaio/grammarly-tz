"""Minimal chat interface for LangGraph Studio."""

from typing import Annotated, Sequence, TypedDict
import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Enable LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "grammarly-support-chatbot"

from src.app import GrammarlySupportChatBot


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


async def chatbot(state: AgentState):
    messages = state["messages"]
    # Get the last human message
    last_msg = messages[-1]
    # Handle both dict and BaseMessage formats
    if isinstance(last_msg, dict):
        last_message = last_msg.get("content", "")
    else:
        last_message = last_msg.content
    
    # Process through the main bot
    bot = GrammarlySupportChatBot()
    result = await bot.process_query(query=last_message)
    
    # Format response
    response = result.get("response", "I apologize, but I couldn't process your request.")
    
    # Add metadata
    if result.get("intent"):
        response += f"\n\n---\n📊 Intent: {result['intent']}"
    if result.get("quality_score") is not None:
        response += f"\n💯 Quality: {result['quality_score']:.0%}"
    
    return {"messages": [AIMessage(content=response)]}


# Create the graph
workflow = StateGraph(AgentState)
workflow.add_node("chatbot", chatbot)
workflow.set_entry_point("chatbot")
workflow.add_edge("chatbot", END)

# Compile
simple_chat = workflow.compile()