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
        content = last_msg.get("content", "")
        # If content is a list (LangGraph format), extract the text
        if isinstance(content, list) and len(content) > 0:
            if isinstance(content[0], dict) and "text" in content[0]:
                last_message = content[0]["text"]
            else:
                last_message = str(content[0])
        else:
            last_message = str(content)
    else:
        last_message = last_msg.content
        # Handle BaseMessage with complex content
        if isinstance(last_message, list) and len(last_message) > 0:
            if isinstance(last_message[0], dict) and "text" in last_message[0]:
                last_message = last_message[0]["text"]
            else:
                last_message = str(last_message[0])
    
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