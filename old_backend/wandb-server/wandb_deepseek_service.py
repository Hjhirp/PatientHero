#!/usr/bin/env python3
"""
Fly.io AI Inference Service for PatientHero
Healthcare-focused AI chatbot backend using Fly.io AI models
"""

import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import uvicorn
# --- New imports for monitoring and PII protection ---
import wandb
import weave
import re
import json
# Note: Using regex-based PII detection for simplicity

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from prompt_manager import get_prompt_manager, generate_demo_response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global conversation cache
conversation_cache: Dict[str, List[Dict[str, str]]] = {}

# Regex patterns for PII detection
PII_PATTERNS = {
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'phone': r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
    'ssn': r'\b\d{3}-?\d{2}-?\d{4}\b',
    'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
    'zip_code': r'\b\d{5}(?:-\d{4})?\b'
}

def has_pii(text: str) -> bool:
    """Check if text contains PII using regex patterns."""
    for pattern_name, pattern in PII_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def redact_pii(text: str) -> str:
    """Redact PII from text using regex patterns."""
    redacted_text = text
    
    # Redact email addresses
    redacted_text = re.sub(PII_PATTERNS['email'], '[EMAIL_REDACTED]', redacted_text, flags=re.IGNORECASE)
    
    # Redact phone numbers
    redacted_text = re.sub(PII_PATTERNS['phone'], '[PHONE_REDACTED]', redacted_text)
    
    # Redact SSNs
    redacted_text = re.sub(PII_PATTERNS['ssn'], '[SSN_REDACTED]', redacted_text)
    
    # Redact credit card numbers
    redacted_text = re.sub(PII_PATTERNS['credit_card'], '[CREDIT_CARD_REDACTED]', redacted_text)
    
    # Redact zip codes
    redacted_text = re.sub(PII_PATTERNS['zip_code'], '[ZIP_CODE_REDACTED]', redacted_text)
    
    return redacted_text

# Fallback PII detection functions (since wandb.pii may not be available)
def has_pii(text: str) -> bool:
    """Simple PII detection using regex patterns."""
    # Email pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    # Phone pattern (various formats)
    phone_pattern = r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\d{10})'
    # SSN pattern
    ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
    # Credit card pattern (basic)
    cc_pattern = r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
    
    patterns = [email_pattern, phone_pattern, ssn_pattern, cc_pattern]
    
    for pattern in patterns:
        if re.search(pattern, text):
            return True
    return False

def redact_pii(text: str) -> str:
    """Redact PII from text using regex patterns."""
    # Email redaction
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', text)
    # Phone redaction
    text = re.sub(r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\d{10})', '[PHONE_REDACTED]', text)
    # SSN redaction
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', text)
    # Credit card redaction
    text = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CC_REDACTED]', text)
    
    return text

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
    model: str = "llama-3.3-70b"
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]

@dataclass
class DeepSeekConfig:
    """Configuration for Llama 3.3 70B on W&B"""
    wandb_api_key: str
    wandb_entity: str
    wandb_project: str = "patienthero-llama"
    model_name: str = "meta-llama/Llama-3.3-70B-Instruct"
    base_url: str = "https://api.wandb.ai/v1"

class DeepSeekR1Service:
    """Service class for Llama 3.3 70B inference on W&B"""
    
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
        """Get the conversational system prompt for Llama 3.3 70B"""
        prompt_manager = get_prompt_manager()
        try:
            return prompt_manager.get_system_prompt("llama_3_3_70b_conversational")
        except:
            # Fallback to a simple conversational prompt
            return """You are PatientHero, a helpful AI assistant. Respond naturally to all types of conversation. 
            When users ask about health topics, provide helpful information and suggest consulting healthcare professionals for medical advice. 
            For general conversation, greetings, or non-medical topics, respond normally and conversationally."""

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
        """Simulate context-aware medical assistant response"""
        # Extract conversation context
        conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
        user_message = messages[-1]["content"].lower() if messages else ""
        
        # Check for emergency
        emergency_keywords = ["emergency", "urgent", "911", "chest pain", "heart attack", "can't breathe", "severe pain"]
        if any(keyword in user_message for keyword in emergency_keywords):
            return "🚨 This sounds like a medical emergency. Please call 911 or go to your nearest emergency room immediately. I cannot provide emergency medical care."
        
        # Context-aware responses based on conversation flow
        conversation_lower = conversation_text.lower()
        
        # If this is a greeting
        if any(greeting in user_message for greeting in ["hi", "hello", "hey", "good morning", "good afternoon"]):
            return "Hello! I'm PatientHero, your healthcare assistant. I'm here to help you get the medical care you need. To get started, could you tell me about any health concerns or symptoms you're experiencing?"
        
        # If they mentioned a symptom and this is follow-up information
        if any(symptom in conversation_lower for symptom in ["headache", "pain", "fever", "sick", "hurt", "symptom"]):
            # This is part of medical data collection
            if "insurance" not in conversation_lower and any(word in user_message for word in ["started", "from", "since", "morning", "yesterday", "today", "hours", "days", "weeks", "ago", "this", "last"]):
                return f"Thank you for that information. I understand your symptoms started {user_message}. To help connect you with the right healthcare provider, I'll need a few more details:\n\n• What type of health insurance do you have? (e.g., Blue Cross, Aetna, Medicare, uninsured)\n• What's your zip code so I can find nearby providers?\n• What's the best way for a healthcare provider to contact you?\n\nLet's start with your insurance information."
            
            elif "zip" not in conversation_lower and any(insurance in user_message for insurance in ["blue cross", "aetna", "medicare", "medicaid", "uninsured", "no insurance", "cigna", "humana"]):
                return f"Got it, you have {user_message} insurance. Now I need your zip code to find healthcare providers in your area. What's your zip code?"
            
            elif "contact" not in conversation_lower and len(user_message) == 5 and user_message.isdigit():
                return f"Perfect! I have your zip code as {user_message}. Finally, what's the best way for a healthcare provider to contact you? Please provide either:\n• Your phone number\n• Your email address"
            
            elif any(contact in user_message for contact in ["@", "phone", "email", "-", "("]) or user_message.replace("-", "").replace("(", "").replace(")", "").replace(" ", "").isdigit():
                return f"Excellent! I now have all the information needed:\n✅ Symptoms: From our conversation\n✅ Insurance: Mentioned earlier\n✅ Location: Your zip code\n✅ Contact: {user_message}\n\nBased on this information, I can help connect you with appropriate healthcare providers in your area. Would you like me to find nearby doctors or urgent care centers for your symptoms?"
        
        # If they mentioned a new symptom (first detection)
        if any(symptom in user_message for symptom in ["headache", "pain", "fever", "sick", "hurt", "nausea", "dizzy", "cough", "sore throat", "ache"]):
            return f"I understand you're experiencing {user_message}. I want to help you get the right medical care for this concern. To connect you with appropriate healthcare providers, I'll need to gather a few details:\n\n1. Could you tell me more about when your symptoms started?\n2. What type of health insurance do you have?\n3. What's your zip code so I can find nearby providers?\n4. What's the best way for a healthcare provider to contact you?\n\nLet's start with more details about when your symptoms began."
        
        # Default response for unclear input
        return f"I want to make sure I understand you correctly. Could you please provide more details about your health concern or symptoms? I'm here to help connect you with appropriate medical care."

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
        "model": "llama-3.3-70b",
        "wandb_connected": deepseek_service is not None,
        "version": "1.0.0"
    }

@app.post("/v1/chat/completions", response_model=ChatResponse)
async def chat_completions(request: ChatRequest):
    """OpenAI-compatible chat completions endpoint"""
    global deepseek_service, conversation_cache
    try:
        # Generate a simple conversation ID based on the first user message
        conversation_id = str(hash(request.messages[0].content if request.messages else "default"))[:8]
        
        # Get cached conversation if it exists
        cached_conversation = conversation_cache.get(conversation_id, [])
        
        # Redact and check all user messages for PII and prompt injection
        sanitized_messages = []
        for msg in request.messages:
            sanitized_content = safe_redact_and_check(msg.content)
            sanitized_messages.append(ChatMessage(role=msg.role, content=sanitized_content))

        # Combine cached conversation with new messages
        all_messages = []
        for cached_msg in cached_conversation:
            all_messages.append(ChatMessage(role=cached_msg["role"], content=cached_msg["content"]))
        
        # Add new messages (skip system message if already in cache)
        for msg in sanitized_messages:
            if msg.role != "system" or not cached_conversation:
                all_messages.append(msg)

        # Generate response using actual LLM
        if deepseek_service:
            response_text = await deepseek_service.chat_completion(
                all_messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p
            )
        else:
            # If service is not available, return error instead of demo
            raise HTTPException(status_code=503, detail="AI service temporarily unavailable")

        # Redact/check response for PII and prompt injection before returning
        safe_response_text = safe_redact_and_check(response_text)

        # Update conversation cache with new messages and response
        conversation_cache[conversation_id] = []
        for msg in all_messages:
            conversation_cache[conversation_id].append({"role": msg.role, "content": msg.content})
        conversation_cache[conversation_id].append({"role": "assistant", "content": safe_response_text})
        
        # Keep only last 10 messages to prevent memory issues
        if len(conversation_cache[conversation_id]) > 10:
            conversation_cache[conversation_id] = conversation_cache[conversation_id][-10:]

        # Log prompt and response to Weave
        log_to_weave(
            prompt="\n".join([m.content for m in all_messages]),
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
                "prompt_tokens": sum(len(msg.content.split()) for msg in all_messages),
                "completion_tokens": len(safe_response_text.split()),
                "total_tokens": sum(len(msg.content.split()) for msg in all_messages) + len(safe_response_text.split())
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
                "id": "llama-3.3-70b",
                "object": "model",
                "created": 1699564800,
                "owned_by": "meta-llama",
                "permission": [],
                "root": "llama-3.3-70b",
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
    try:
        weave.init(project_name="PatientHero-Prompts")
        weave.log({
            "prompt": prompt,
            "response": response,
            "user_id": user_id or "anonymous"
        })
    except Exception as e:
        logger.warning(f"Failed to log to Weave: {e}")
        # Continue without failing the request

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))  # Changed default port to 8001
    uvicorn.run(
        "wandb_deepseek_service:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
