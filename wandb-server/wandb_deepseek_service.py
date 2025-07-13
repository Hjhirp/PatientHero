#!/usr/bin/env python3
"""
DeepSeek R1 on W&B Inference Service for PatientHero
Healthcare-focused AI chatbot backend using DeepSeek R1 model
"""

import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import wandb
import requests
import uvicorn
# --- New imports for monitoring and PII protection ---
import weave
from wandb.pii import redact_pii, has_pii

from prompt_manager import get_prompt_manager, generate_demo_response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PatientHero - DeepSeek R1 Medical AI",
    description="Healthcare chatbot powered by DeepSeek R1 on Weights & Biases",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API
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
    model: str = "deepseek-r1"
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]

@dataclass
class DeepSeekConfig:
    """Configuration for DeepSeek R1 on W&B"""
    wandb_api_key: str
    wandb_entity: str
    wandb_project: str = "patienthero-deepseek"
    model_name: str = "deepseek-ai/deepseek-r1"
    base_url: str = "https://api.wandb.ai/v1"

class DeepSeekR1Service:
    """Service class for DeepSeek R1 inference on W&B"""
    
    def __init__(self, config: DeepSeekConfig):
        self.config = config
        self.wandb_run = None
        self._initialize_wandb()
    
    def _initialize_wandb(self):
        """Initialize W&B connection"""
        try:
            # Skip W&B initialization if no API key or entity
            if not self.config.wandb_api_key or self.config.wandb_api_key == "your_wandb_api_key_here":
                logger.info("W&B API key not configured - skipping W&B initialization")
                return
            
            if not self.config.wandb_entity or self.config.wandb_entity == "your_wandb_username_or_team":
                logger.info("W&B entity not configured - skipping W&B initialization")
                return
            
            wandb.login(key=self.config.wandb_api_key)
            self.wandb_run = wandb.init(
                project=self.config.wandb_project,
                entity=self.config.wandb_entity,
                job_type="inference",
                name="deepseek-r1-medical-chat",
                mode="online"  # Ensure we're in online mode
            )
            logger.info("W&B initialized successfully")
        except Exception as e:
            logger.warning(f"W&B initialization failed: {e} - continuing in demo mode")
            self.wandb_run = None
    
    def get_medical_system_prompt(self) -> str:
        """Get the medical-focused system prompt for DeepSeek R1"""
        prompt_manager = get_prompt_manager()
        return prompt_manager.get_system_prompt("deepseek_r1_medical")

    async def chat_completion(self, messages: List[ChatMessage], **kwargs) -> str:
        """Generate chat completion using DeepSeek R1 via W&B"""
        try:
            # Redact PII from user messages before sending to LLM
            redacted_messages = []
            for msg in messages:
                if msg.role == "user":
                    redacted_content = redact_pii(msg.content)
                else:
                    redacted_content = msg.content
                redacted_messages.append(ChatMessage(role=msg.role, content=redacted_content))

            # Prepare messages with medical system prompt
            formatted_messages = self._format_messages(redacted_messages)
            
            # Log the conversation to W&B
            if self.wandb_run:
                wandb.log({
                    "conversation_length": len(formatted_messages),
                    "user_message": formatted_messages[-1]["content"] if formatted_messages else "",
                    "model": self.config.model_name
                })
            
            # Use W&B inference API
            response = await self._call_wandb_inference(formatted_messages, **kwargs)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            raise
    
    def _format_messages(self, messages: List[ChatMessage]) -> List[Dict[str, str]]:
        """Format messages for DeepSeek R1"""
        formatted = []
        
        # Add system message if not present
        has_system = any(msg.role == "system" for msg in messages)
        if not has_system:
            formatted.append({
                "role": "system",
                "content": self.get_medical_system_prompt()
            })
        
        # Add user messages
        for msg in messages:
            formatted.append({
                "role": msg.role,
                "content": msg.content
            })
        
        return formatted
    
    async def _call_wandb_inference(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Call W&B inference API for DeepSeek R1"""
        try:
            # W&B inference endpoint (this is a placeholder - adjust based on actual W&B API)
            url = f"{self.config.base_url}/inference"
            
            headers = {
                "Authorization": f"Bearer {self.config.wandb_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.config.model_name,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", 512),
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.9)
            }
            
            # For now, simulate a medical response (replace with actual W&B API call)
            response = await self._simulate_deepseek_response(messages)
            return response
            
        except Exception as e:
            logger.error(f"W&B inference API error: {e}")
            raise
    
    async def _simulate_deepseek_response(self, messages: List[Dict[str, str]]) -> str:
        """Simulate DeepSeek R1 response using prompt manager"""
        user_message = messages[-1]["content"] if messages else ""
        prompt_manager = get_prompt_manager()
        
        # Use prompt manager to generate appropriate response
        return prompt_manager.generate_response(user_message, "DeepSeek R1")

# Global service instance
deepseek_service: Optional[DeepSeekR1Service] = None

def generate_demo_medical_response(user_message: str) -> str:
    """Generate a demo medical response when W&B is not configured"""
    return generate_demo_response(user_message, "DeepSeek R1 (Demo Mode)")

@app.on_event("startup")
async def startup_event():
    """Initialize DeepSeek R1 service on startup"""
    global deepseek_service
    
    # Get configuration from environment
    config = DeepSeekConfig(
        wandb_api_key=os.getenv("WANDB_API_KEY", ""),
        wandb_entity=os.getenv("WANDB_ENTITY", ""),
        wandb_project=os.getenv("WANDB_PROJECT", "patienthero-deepseek")
    )
    
    if not config.wandb_api_key or config.wandb_api_key == "your_wandb_api_key_here":
        logger.info("WANDB_API_KEY not set - running in demo mode")
    
    if not config.wandb_entity or config.wandb_entity == "your_wandb_username_or_team":
        logger.info("WANDB_ENTITY not set - running in demo mode")
    
    try:
        deepseek_service = DeepSeekR1Service(config)
        logger.info("DeepSeek R1 service initialized successfully")
    except Exception as e:
        logger.warning(f"DeepSeek R1 service initialization had issues: {e} - continuing in demo mode")
        # Create a minimal service instance for demo mode
        deepseek_service = None

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "PatientHero - DeepSeek R1 Medical AI",
        "model": "deepseek-r1",
        "status": "running",
        "wandb_connected": deepseek_service is not None
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "model": "deepseek-r1",
        "wandb_connected": deepseek_service is not None,
        "version": "1.0.0"
    }

@app.post("/v1/chat/completions", response_model=ChatResponse)
async def chat_completions(request: ChatRequest):
    """OpenAI-compatible chat completions endpoint"""
    global deepseek_service
    try:
        # Redact and check all user messages for PII and prompt injection
        sanitized_messages = []
        for msg in request.messages:
            sanitized_content = safe_redact_and_check(msg.content)
            sanitized_messages.append(ChatMessage(role=msg.role, content=sanitized_content))

        # Generate response
        if deepseek_service:
            response_text = await deepseek_service.chat_completion(
                sanitized_messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p
            )
        else:
            # Redact PII before demo response
            user_message = sanitized_messages[-1].content if sanitized_messages else ""
            user_message = redact_pii(user_message)
            response_text = generate_demo_medical_response(user_message)

        # Redact/check response for PII and prompt injection before returning
        safe_response_text = safe_redact_and_check(response_text)

        # Log prompt and response to Weave
        log_to_weave(
            prompt="\n".join([m.content for m in sanitized_messages]),
            response=safe_response_text
        )

        # Format response
        return ChatResponse(
            id=f"chatcmpl-{hash(str(request.messages)) % 1000000}",
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": safe_response_text
                },
                "finish_reason": "stop"
            }],
            usage={
                "prompt_tokens": sum(len(msg.content.split()) for msg in sanitized_messages),
                "completion_tokens": len(safe_response_text.split()),
                "total_tokens": sum(len(msg.content.split()) for msg in sanitized_messages) + len(safe_response_text.split())
            }
        )
    except Exception as e:
        logger.error(f"Error in chat completion: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI-compatible)"""
    return {
        "object": "list",
        "data": [
            {
                "id": "deepseek-r1",
                "object": "model",
                "created": 1699564800,
                "owned_by": "deepseek-ai",
                "permission": [],
                "root": "deepseek-r1",
                "parent": None
            }
        ]
    }

def is_prompt_injection(text: str) -> bool:
    """Detect basic prompt injection attempts."""
    # Simple heuristic: look for suspicious prompt injection patterns
    injection_patterns = [
        "ignore previous instructions", "disregard above", "override", "forget previous", "as an ai", "repeat this prompt", "simulate", "act as", "you are now"
    ]
    lowered = text.lower()
    return any(pattern in lowered for pattern in injection_patterns)


def safe_redact_and_check(text: str) -> str:
    """Redact PII and block prompt injection."""
    if is_prompt_injection(text):
        return "[Blocked: Potential prompt injection detected.]"
    if has_pii(text):
        return redact_pii(text)
    return text


def log_to_weave(prompt: str, response: str, user_id: Optional[str] = None):
    """Log prompt and response to Weave for monitoring."""
    weave.init(project="PatientHero-Prompts")
    weave.log({
        "prompt": prompt,
        "response": response,
        "user_id": user_id or "anonymous"
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))  # Changed default port to 8001
    uvicorn.run(
        "wandb_deepseek_service:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
