from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
import logging
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PatientHero Med42-8B API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for model and tokenizer
tokenizer = None
model = None

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

def load_model():
    """Load the Med42-8B model with optimizations for deployment."""
    global tokenizer, model
    
    model_name = "m42-health/Llama3-Med42-8B"  # Using 8B for better performance
    
    logger.info(f"Loading model: {model_name}")
    
    # Check if CUDA is available
    has_cuda = torch.cuda.is_available()
    logger.info(f"CUDA available: {has_cuda}")
    
    try:
        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True,
            cache_dir="/app/cache"
        )
        
        # Set pad token if not present
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        # Load model with appropriate configuration
        if has_cuda:
            # Configure quantization for memory efficiency (GPU)
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
            )
            
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                quantization_config=quantization_config,
                device_map="auto",
                trust_remote_code=True,
                torch_dtype=torch.float16,
                cache_dir="/app/cache"
            )
        else:
            # CPU-only deployment - use reduced precision
            logger.info("Loading model for CPU deployment...")
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                trust_remote_code=True,
                torch_dtype=torch.float32,
                device_map="cpu",
                cache_dir="/app/cache",
                low_cpu_mem_usage=True
            )
        
        logger.info("Med42-8B model loaded successfully!")
        
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        raise e

def format_chat_prompt(messages: List[ChatMessage]) -> str:
    """Format chat messages into a prompt suitable for Llama3-Med42-70B."""
    system_message = "You are Med42, a helpful and knowledgeable medical AI assistant. Provide accurate, evidence-based medical information while being empathetic and professional. Always remind users to consult healthcare professionals for medical advice."
    
    # Find system message if provided
    for msg in messages:
        if msg.role == "system":
            system_message = msg.content
            break
    
    # Build conversation
    conversation = f"System: {system_message}\n\n"
    
    for message in messages:
        if message.role != "system":
            role = "Human" if message.role == "user" else "Assistant"
            conversation += f"{role}: {message.content}\n\n"
    
    conversation += "Assistant:"
    return conversation

@app.on_event("startup")
async def startup_event():
    """Load the model when the server starts."""
    load_model()

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Med42-8B API is running", "model": "m42-health/Llama3-Med42-8B"}

@app.get("/health")
async def health_check():
    """Detailed health check."""
    global model, tokenizer
    
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "tokenizer_loaded": tokenizer is not None,
        "gpu_available": torch.cuda.is_available(),
        "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
    }

@app.post("/v1/chat/completions", response_model=ChatResponse)
async def chat_completions(request: ChatRequest):
    """OpenAI-compatible chat completions endpoint."""
    global model, tokenizer
    
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Format the prompt
        prompt = format_chat_prompt(request.messages)
        
        # Tokenize input
        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=4096,
            padding=True
        )
        
        # Move to GPU if available
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        # Generate response
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                do_sample=True,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
                repetition_penalty=1.1
            )
        
        # Decode response
        generated_tokens = outputs[0][inputs['input_ids'].shape[1]:]
        response_text = tokenizer.decode(generated_tokens, skip_special_tokens=True)
        
        # Clean up response
        response_text = response_text.strip()
        
        # Calculate token usage
        input_tokens = inputs['input_ids'].shape[1]
        output_tokens = len(generated_tokens)
        
        return ChatResponse(
            id=f"chatcmpl-{hash(prompt) % 1000000}",
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
        "server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        workers=1
    )
