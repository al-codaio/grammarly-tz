"""FastAPI server for the Grammarly support chatbot."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.app import GrammarlySupportChatBot
from src.state import Message


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Grammarly Support Chatbot API",
    description="AI-powered customer support chatbot with TensorZero optimization",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize chatbot
chatbot = GrammarlySupportChatBot()


# Request/Response models
class ChatRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    episode_id: Optional[str] = None
    user_context: Optional[Dict[str, Any]] = None
    variant: Optional[str] = None


class ChatResponse(BaseModel):
    conversation_id: str
    episode_id: str
    response: str
    intent: Optional[str]
    requires_human: bool
    quality_score: Optional[float]
    suggested_actions: List[str]
    knowledge_articles: List[Dict[str, Any]]
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    services: Dict[str, bool]


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    from utils.tensorzero_client import TensorZeroClient
    
    services = {
        "api": True,
        "tensorzero": False,
        "langgraph": True
    }
    
    # Check TensorZero connection
    try:
        async with TensorZeroClient() as client:
            services["tensorzero"] = await client.health_check()
    except Exception as e:
        logger.error(f"TensorZero health check failed: {e}")
    
    all_healthy = all(services.values())
    
    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        timestamp=datetime.utcnow().isoformat(),
        services=services
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a customer support query."""
    try:
        # Process the query
        result = await chatbot.process_query(
            query=request.query,
            conversation_id=request.conversation_id,
            episode_id=request.episode_id,
            user_context=request.user_context
        )
        
        # Check for errors in result
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return ChatResponse(
            conversation_id=result["conversation_id"],
            episode_id=result["episode_id"],
            response=result["response"] or "I apologize, but I couldn't generate a response. Please try again.",
            intent=result.get("intent"),
            requires_human=result.get("requires_human", False),
            quality_score=result.get("quality_score"),
            suggested_actions=result.get("suggested_actions", []),
            knowledge_articles=result.get("knowledge_articles", []),
            timestamp=datetime.utcnow().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation history."""
    try:
        # In production, this would fetch from the checkpointer
        return {
            "conversation_id": conversation_id,
            "messages": [],  # Placeholder
            "status": "not_implemented"
        }
    except Exception as e:
        logger.error(f"Error fetching conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feedback")
async def submit_feedback(
    inference_id: str,
    metric_name: str,
    value: Any,
    episode_id: Optional[str] = None
):
    """Submit feedback for an inference."""
    from utils.tensorzero_client import TensorZeroClient
    
    try:
        async with TensorZeroClient() as client:
            result = await client.send_feedback(
                inference_id=inference_id,
                metric_name=metric_name,
                value=value,
                episode_id=episode_id
            )
        
        return {"status": "success", "result": result}
    
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Grammarly Support Chatbot",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/chat",
            "health": "/health",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)