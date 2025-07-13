from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
import logging
import hashlib
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PatientHero Med42-8B API (Demo)", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    role: str  # "user", "assistant", or "system"
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.9
    stream: Optional[bool] = False

class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    model: str = "m42-health/Llama3-Med42-8B"
    choices: List[dict]
    usage: dict

def generate_medical_response(user_message: str) -> str:
    """Generate a demo medical response based on user input."""
    user_lower = user_message.lower()
    
    # Simple keyword-based responses for demo
    if any(word in user_lower for word in ['headache', 'head', 'migraine']):
        return """Headaches can have various causes including:

• **Tension headaches**: Often caused by stress, dehydration, or muscle tension
• **Dehydration**: Very common cause, especially if you haven't had enough water
• **Sleep issues**: Lack of sleep or poor sleep quality
• **Stress**: Physical or emotional stress can trigger headaches

**General recommendations:**
• Stay well hydrated (8-10 glasses of water daily)
• Get adequate sleep (7-9 hours)
• Try relaxation techniques
• Consider if you've eaten regularly

**When to seek medical care:**
• Sudden, severe headache unlike any before
• Headache with fever, stiff neck, or vision changes
• Frequent or worsening headaches
• Headache after head injury"""

    elif any(word in user_lower for word in ['stomach', 'belly', 'gas', 'nausea', 'abdomen']):
        return """Stomach discomfort and gas can be caused by:

• **Dietary factors**: Eating too quickly, certain foods, or food intolerances
• **Digestive issues**: Normal digestion processes or mild irritation
• **Stress**: Can affect digestion and cause stomach upset
• **Hydration**: Dehydration can affect digestion

**General recommendations:**
• Eat slowly and chew food thoroughly
• Stay hydrated with water
• Avoid foods that commonly cause gas (beans, carbonated drinks, etc.)
• Try gentle movement like walking
• Consider if stress might be a factor

**When to seek medical care:**
• Severe or persistent pain
• Vomiting that won't stop
• Signs of dehydration
• Pain with fever"""

    elif any(word in user_lower for word in ['fever', 'temperature', 'hot', 'chills']):
        return """Fever is often your body's natural response to infection:

• **Common causes**: Viral or bacterial infections, inflammation
• **Normal range**: 98.6°F (37°C) is average, but varies by person
• **Low-grade fever**: 100.4°F (38°C) or slightly above

**General care:**
• Rest and stay hydrated
• Monitor temperature regularly
• Light clothing and cool environment
• Over-the-counter fever reducers if appropriate

**When to seek medical care:**
• Fever over 103°F (39.4°C)
• Fever lasting more than 3 days
• Difficulty breathing or chest pain
• Severe headache or stiff neck
• Signs of dehydration"""

    else:
        return f"""Based on your concern about "{user_message}", here's some general health information:

**Common steps for many health concerns:**
• Monitor your symptoms and how they change
• Stay well hydrated and get adequate rest
• Consider any recent changes in diet, stress, or routine
• Note if symptoms worsen or improve

**General wellness tips:**
• Maintain good hydration (8-10 glasses of water daily)
• Get regular sleep (7-9 hours per night)
• Eat balanced, regular meals
• Manage stress through relaxation or exercise

**When to seek professional medical care:**
• Symptoms that are severe or getting worse
• Symptoms that persist beyond a few days
• Any symptoms that concern you or interfere with daily activities
• Emergency symptoms like difficulty breathing, chest pain, or severe pain

If you're concerned about your symptoms, consider consulting with a healthcare provider who can properly evaluate your specific situation."""

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "PatientHero Med42-8B API (Demo Mode)",
        "model": "m42-health/Llama3-Med42-8B",
        "status": "running",
        "mode": "demo"
    }

@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "model": "m42-health/Llama3-Med42-8B",
        "mode": "demo",
        "version": "1.0.0"
    }

@app.post("/v1/chat/completions", response_model=ChatResponse)
async def chat_completions(request: ChatRequest):
    """OpenAI-compatible chat completions endpoint."""
    try:
        # Get the last user message
        user_message = ""
        for msg in reversed(request.messages):
            if msg.role == "user":
                user_message = msg.content
                break
        
        if not user_message:
            user_message = "general health question"
        
        # Generate medical response
        response_text = generate_medical_response(user_message)
        
        # Calculate token usage (approximate)
        input_tokens = sum(len(msg.content.split()) for msg in request.messages)
        output_tokens = len(response_text.split())
        
        return ChatResponse(
            id=f"chatcmpl-{hashlib.md5(user_message.encode()).hexdigest()[:8]}",
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }],
            usage={
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI-compatible)."""
    return {
        "object": "list",
        "data": [
            {
                "id": "m42-health/Llama3-Med42-8B",
                "object": "model",
                "created": 1699564800,
                "owned_by": "m42-health",
                "permission": [],
                "root": "m42-health/Llama3-Med42-8B",
                "parent": None
            }
        ]
    }

if __name__ == "__main__":
    uvicorn.run(
        "server_demo:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        workers=1
    )
