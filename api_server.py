#!/usr/bin/env python
"""
FastAPI backend server for PatientHero CrewAI integration
Provides REST API endpoints for the Next.js frontend
"""

import os
import sys
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
import weave
import re
import wandb
from datetime import datetime

# Add the crewai_agents directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'crewai_agents'))

try:
    from crewai_agents.main import PatientHeroCrewAI
except ImportError as e:
    print(f"Error importing PatientHeroCrewAI: {e}")
    print("Make sure you're running this from the PatientHero root directory")
    sys.exit(1)

# Pydantic models for request/response
class ChatRequest(BaseModel):
    user_input: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    agent: str
    response: str
    patient_data: Dict[str, Any]
    next_step: str
    extraction_data: Optional[Dict[str, Any]] = None
    guardrail_triggered: Optional[bool] = False
    guardrail_warning: Optional[str] = None

class StatusResponse(BaseModel):
    session_id: str
    basic_info_complete: bool
    patient_data: Dict[str, Any]
    next_step: str

# FastAPI app
app = FastAPI(
    title="PatientHero CrewAI API",
    description="Backend API for PatientHero medical consultation system",
    version="1.0.0"
)

# Initialize Weave and Wandb for monitoring
try:
    import weave
    import wandb
    
    # Initialize wandb first
    wandb.init(
        project="patienthero-crewai",
        name=f"guardrail-session-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        config={
            "service": "api-server",
            "guardrails": "enabled",
            "version": "1.0.0"
        }
    )
    
    # Initialize weave with same project
    weave.init("patienthero-crewai")
    print("✅ Weave and W&B monitoring initialized")
except ImportError:
    print("⚠️ Weave/W&B not available - monitoring disabled")
    wandb = None
    weave = None
except Exception as e:
    print(f"❌ Monitoring initialization failed: {e}")
    wandb = None
    weave = None

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Next.js dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global store for PatientHero instances (in production, use Redis or database)
patient_sessions: Dict[str, PatientHeroCrewAI] = {}

# Global counters for session tracking
session_counters = {}

# Enhanced Guardrail validation functions with consistent W&B logging
class GuardrailValidator:
    @staticmethod
    def log_guardrail_event(event_type: str, input_text: str, reason: str, severity: str = "medium", blocked: bool = True):
        """Log guardrail events to W&B for monitoring with consistent structure"""
        if wandb and wandb.run:
            # Get session counter for step-based logging
            session_id = getattr(wandb.run, 'current_session_id', 'default')
            if session_id not in session_counters:
                session_counters[session_id] = 0
            session_counters[session_id] += 1
            
            # Core guardrail metrics with step
            guardrail_data = {
                "guardrail_triggered": 1 if blocked else 0,
                "guardrail_passed": 0 if blocked else 1,
                "event_type": event_type,
                "severity": severity,
                "input_length": len(input_text),
                "action": "blocked" if blocked else "allowed",
                "session_id": session_id,
                "interaction_step": session_counters[session_id]
            }
            wandb.log(guardrail_data, step=session_counters[session_id])
            
            # Always append to guardrail events table
            if not hasattr(wandb.run, 'guardrail_table'):
                wandb.run.guardrail_table = wandb.Table(
                    columns=["step", "timestamp", "session_id", "event_type", "severity", "action", "reason", "input_preview"]
                )
            
            wandb.run.guardrail_table.add_data(
                session_counters[session_id],
                datetime.now().isoformat(),
                session_id,
                event_type,
                severity,
                "BLOCKED" if blocked else "ALLOWED",
                reason,
                input_text[:150] + "..." if len(input_text) > 150 else input_text
            )
            wandb.log({"guardrail_events_table": wandb.run.guardrail_table}, step=session_counters[session_id])
            
            # Cumulative counts by severity
            severity_key = f"total_guardrail_{severity}_count"
            current_count = getattr(wandb.run, severity_key, 0) + 1
            setattr(wandb.run, severity_key, current_count)
            wandb.log({severity_key: current_count}, step=session_counters[session_id])
    
    @staticmethod
    def validate_user_input(user_input: str) -> tuple[bool, Optional[str]]:
        """Validate user input for safety and appropriateness"""
        user_input_lower = user_input.lower()
        
        # Check for inappropriate content
        inappropriate_patterns = [
            (r'\b(kill|suicide|harm|hurt)\s+(myself|me)\b', "suicide_ideation", "critical"),
            (r'\b(want to die|end my life)\b', "suicide_ideation", "critical"),
            (r'\b(illegal drugs|street drugs)\b', "illegal_content", "high"),
            (r'\b(prescription fraud|fake prescription)\b', "illegal_content", "high"),
            (r'\b(take|ingest|swallow)\s+(\d{2,}|\d+\s+(pills|tablets))\b', "dangerous_dosage", "critical"),
            (r'\b(\d{2,})\s+(pills|tablets|capsules)\b', "dangerous_dosage", "critical"),
            (r'\bwhole bottle\b.*\b(pills|medication)\b', "dangerous_dosage", "critical")
        ]
        
        for pattern, event_type, severity in inappropriate_patterns:
            if re.search(pattern, user_input_lower):
                if 'suicide' in pattern or 'kill' in pattern or 'die' in pattern:
                    reason = "I'm concerned about your safety. Please contact emergency services (911) or a crisis helpline if you're in immediate danger."
                    GuardrailValidator.log_guardrail_event(event_type, user_input, reason, severity, blocked=True)
                    return False, reason
                elif 'dosage' in event_type or 'pills' in pattern or 'bottle' in pattern:
                    reason = "I'm very concerned about this request. Taking large amounts of medication can be extremely dangerous. Please contact emergency services (911) or poison control (1-800-222-1222) immediately if you're considering this."
                    GuardrailValidator.log_guardrail_event(event_type, user_input, reason, severity, blocked=True)
                    return False, reason
                else:
                    reason = "I can only provide information about legal medical treatments and services."
                    GuardrailValidator.log_guardrail_event(event_type, user_input, reason, severity, blocked=True)
                    return False, reason
        
        # Check for medical advice requests
        medical_advice_patterns = [
            (r'\bshould i take\b.*\b(medication|pills|drugs)\b', "medical_advice_request"),
            (r'\bwhat medication\b', "medical_advice_request"),
            (r'\bhow much\b.*\b(dosage|dose)\b', "dosage_request"),
            (r'\bdiagnose me\b', "diagnosis_request"),
            (r'\bis it cancer\b', "diagnosis_request")
        ]
        
        for pattern, event_type in medical_advice_patterns:
            if re.search(pattern, user_input_lower):
                reason = "I cannot provide specific medical advice or diagnoses. Please consult with a healthcare professional for medical guidance."
                GuardrailValidator.log_guardrail_event(event_type, user_input, reason, "high", blocked=True)
                return False, reason
        
        # Log successful validation (no guardrails triggered)
        GuardrailValidator.log_guardrail_event("input_validation", user_input, "Input passed all safety checks", "info", blocked=False)
        return True, None
    
    @staticmethod
    def validate_ai_response(response: str) -> tuple[bool, Optional[str]]:
        """Validate AI response for medical accuracy and safety"""
        response_lower = response.lower()
        
        # Check for potential medical misinformation
        problematic_phrases = [
            (r'\byou have\b.*\b(cancer|diabetes|heart disease)\b', "diagnosis_given"),
            (r'\byou are diagnosed with\b', "diagnosis_given"),
            (r'\btake this medication\b', "medication_advice"),
            (r'\bstop taking your medication\b', "medication_advice"),
            (r'\byou don\'t need a doctor\b', "medical_dismissal"),
            (r'\bthis will cure\b', "cure_claims"),
            (r'\bguaranteed to work\b', "guarantee_claims")
        ]
        
        for phrase, event_type in problematic_phrases:
            if re.search(phrase, response_lower):
                reason = "Response contains potential medical advice that requires professional consultation."
                GuardrailValidator.log_guardrail_event(f"ai_response_{event_type}", response, reason, "high", blocked=True)
                return False, reason
        
        # Only require disclaimers for specific medical advice, not general information
        giving_specific_advice = any(advice in response_lower for advice in [
            'you should take', 'i recommend', 'my advice is', 'you need to', 'definitely do this'
        ])
        
        # Check for appropriate disclaimers only when giving specific advice
        if giving_specific_advice:
            has_disclaimer = any(disclaimer in response_lower for disclaimer in [
                'consult', 'healthcare provider', 'medical professional', 'doctor', 'emergency'
            ])
            
            if not has_disclaimer:
                reason = "Medical advice should include appropriate disclaimers about consulting healthcare professionals."
                GuardrailValidator.log_guardrail_event("ai_response_missing_disclaimer", response, reason, "medium", blocked=True)
                return False, reason
        
        # Log successful AI response validation
        GuardrailValidator.log_guardrail_event("ai_response_validation", response, "AI response passed all safety checks", "info", blocked=False)
        return True, None

@app.get("/")
async def root():
    return {
        "message": "PatientHero CrewAI API",
        "status": "running",
        "endpoints": [
            "/api/chat",
            "/api/status/{session_id}",
            "/api/institutions/{session_id}",
            "/docs"
        ]
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint that processes user input through CrewAI agents
    """
    try:
        session_id = request.session_id or "temp"
        
        # Initialize session counter and set current session for logging
        if session_id not in session_counters:
            session_counters[session_id] = 0
        session_counters[session_id] += 1
        
        # Set current session for guardrail logging
        if wandb and wandb.run:
            wandb.run.current_session_id = session_id
        
        # Log the incoming request for ALL interactions with step
        if wandb and wandb.run:
            current_step = session_counters[session_id]
            
            wandb.log({
                "api_request": 1,
                "input_length": len(request.user_input),
                "has_session": request.session_id is not None,
                "request_type": "chat_interaction",
                "session_id": session_id,
                "interaction_number": current_step
            }, step=current_step)
            
            # Always append to interactions table
            if not hasattr(wandb.run, 'interactions_table'):
                wandb.run.interactions_table = wandb.Table(
                    columns=["step", "timestamp", "session_id", "input_text", "input_length", "interaction_type"]
                )
            
            wandb.run.interactions_table.add_data(
                current_step,
                datetime.now().isoformat(),
                session_id,
                request.user_input[:200] + "..." if len(request.user_input) > 200 else request.user_input,
                len(request.user_input),
                "user_input"
            )
            wandb.log({"all_interactions_table": wandb.run.interactions_table}, step=current_step)
        
        # Validate user input with guardrails
        input_valid, input_warning = GuardrailValidator.validate_user_input(request.user_input)
        if not input_valid:
            # Log guardrail blocking
            if wandb and wandb.run:
                wandb.log({
                    "guardrail_blocked_interaction": 1,
                    "session_id": session_id,
                    "blocking_reason": input_warning[:100] + "..." if len(input_warning) > 100 else input_warning
                }, step=session_counters[session_id])
            
            return ChatResponse(
                agent="guardrail_system",
                response=input_warning,
                patient_data={"session_id": session_id},
                next_step="input_validation_failed",
                guardrail_triggered=True,
                guardrail_warning=input_warning
            )
        
        # Get or create PatientHero instance for this session
        if session_id and session_id in patient_sessions:
            patient_hero = patient_sessions[session_id]
        else:
            patient_hero = PatientHeroCrewAI()
            session_id = patient_hero.patient_data.session_id
            patient_sessions[session_id] = patient_hero
            # Update session counter for new session
            if session_id not in session_counters:
                session_counters[session_id] = session_counters.get(request.session_id or "temp", 0)
        
        # Process user input through CrewAI
        response = patient_hero.process_user_input(request.user_input)
        
        # Validate AI response with guardrails
        response_valid, response_warning = GuardrailValidator.validate_ai_response(response['response'])
        if not response_valid:
            # Log AI response guardrail blocking
            if wandb and wandb.run:
                wandb.log({
                    "ai_response_blocked": 1,
                    "session_id": session_id,
                    "blocking_reason": response_warning[:100] + "..." if len(response_warning) > 100 else response_warning
                }, step=session_counters[session_id])
            
            return ChatResponse(
                agent="guardrail_system",
                response="I apologize, but I need to be more careful with my response. Let me rephrase that to ensure I'm providing safe and appropriate information. Please consult with a healthcare professional for specific medical advice.",
                patient_data=response['patient_data'],
                next_step=response['next_step'],
                guardrail_triggered=True,
                guardrail_warning=response_warning
            )
        
        # Log successful interaction with detailed metrics
        if wandb and wandb.run:
            current_step = session_counters[session_id]
            
            wandb.log({
                "successful_interaction": 1,
                "agent_type": response['agent'],
                "response_length": len(response['response']),
                "session_id": session_id,
                "guardrail_passed": True,
                "total_session_interactions": current_step
            }, step=current_step)
            
            # Add AI response to interactions table
            wandb.run.interactions_table.add_data(
                current_step,
                datetime.now().isoformat(),
                session_id,
                response['response'][:200] + "..." if len(response['response']) > 200 else response['response'],
                len(response['response']),
                f"ai_response_{response['agent']}"
            )
            wandb.log({"all_interactions_table": wandb.run.interactions_table}, step=current_step)
            
            # Create conversation flow table
            if not hasattr(wandb.run, 'conversation_table'):
                wandb.run.conversation_table = wandb.Table(
                    columns=["step", "timestamp", "session_id", "user_input", "agent", "ai_response", "guardrails_passed"]
                )
            
            wandb.run.conversation_table.add_data(
                current_step,
                datetime.now().isoformat(),
                session_id,
                request.user_input[:150] + "..." if len(request.user_input) > 150 else request.user_input,
                response['agent'],
                response['response'][:150] + "..." if len(response['response']) > 150 else response['response'],
                "✅ PASSED"
            )
            wandb.log({"conversation_flow_table": wandb.run.conversation_table}, step=current_step)
        
        return ChatResponse(
            agent=response['agent'],
            response=response['response'],
            patient_data=response['patient_data'],
            next_step=response['next_step'],
            extraction_data=response.get('extraction_data'),
            guardrail_triggered=False
        )
        
    except Exception as e:
        # Log errors to W&B with step
        if wandb and wandb.run:
            error_step = session_counters.get(session_id, 0)
            wandb.log({
                "api_error": 1,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "session_id": session_id
            }, step=error_step)
        
        print(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/status/{session_id}", response_model=StatusResponse)
async def get_status(session_id: str):
    """
    Get current patient data status for a session
    """
    try:
        if session_id not in patient_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        patient_hero = patient_sessions[session_id]
        status = patient_hero.get_patient_status()
        
        return StatusResponse(
            session_id=status['session_id'],
            basic_info_complete=status['basic_info_complete'],
            patient_data=status['patient_data'],
            next_step=status['next_step']
        )
        
    except Exception as e:
        print(f"Error in status endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/institutions/{session_id}")
async def search_institutions(session_id: str, medical_condition: str, zip_code: str, insurance: Optional[str] = None):
    """
    Search for nearby medical institutions using ExaHelper
    """
    try:
        if session_id not in patient_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        patient_hero = patient_sessions[session_id]
        institutions = patient_hero.search_nearby_institutions(
            medical_condition=medical_condition,
            zip_code=zip_code,
            insurance=insurance
        )
        
        return {
            "session_id": session_id,
            "institutions": institutions,
            "search_params": {
                "medical_condition": medical_condition,
                "zip_code": zip_code,
                "insurance": insurance
            }
        }
        
    except Exception as e:
        print(f"Error in institutions endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete("/api/session/{session_id}")
async def end_session(session_id: str):
    """
    End a patient session and clean up resources
    """
    try:
        if session_id in patient_sessions:
            del patient_sessions[session_id]
            return {"message": f"Session {session_id} ended successfully"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
            
    except Exception as e:
        print(f"Error ending session: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/sessions")
async def list_sessions():
    """
    List all active sessions (for debugging)
    """
    return {
        "active_sessions": list(patient_sessions.keys()),
        "session_count": len(patient_sessions)
    }

@app.get("/api/guardrails/status")
async def guardrail_status():
    """
    Get guardrail system status and statistics
    """
    return {
        "guardrail_system": "active",
        "wandb_logging": wandb is not None and wandb.run is not None,
        "weave_logging": weave is not None,
        "validation_checks": [
            "inappropriate_content",
            "medical_advice_detection", 
            "safety_concerns",
            "response_validation"
        ],
        "safety_features": [
            "suicide_prevention",
            "illegal_content_filtering",
            "medical_disclaimer_enforcement"
        ],
        "logging_features": [
            "guardrail_triggers",
            "interaction_metrics",
            "error_tracking",
            "event_classification"
        ]
    }

@app.get("/api/metrics/dashboard")
async def metrics_dashboard():
    """
    Get W&B dashboard URL for monitoring
    """
    if wandb and wandb.run:
        return {
            "wandb_url": wandb.run.url,
            "project_url": f"https://wandb.ai/{wandb.run.entity}/{wandb.run.project}",
            "run_name": wandb.run.name,
            "status": "active"
        }
    else:
        return {
            "status": "inactive",
            "message": "W&B logging not initialized"
        }

@app.get("/api/session/{session_id}/summary")
async def session_summary(session_id: str):
    """
    Get comprehensive session summary with all interactions
    """
    try:
        if session_id not in patient_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        patient_hero = patient_sessions[session_id]
        interaction_count = session_counters.get(session_id, 0)
        
        # Log session summary to W&B
        if wandb and wandb.run:
            wandb.log({
                "session_summary_requested": 1,
                "session_id": session_id,
                "total_interactions": interaction_count,
                "session_duration_check": datetime.now().isoformat()
            }, step=interaction_count)
        
        return {
            "session_id": session_id,
            "total_interactions": interaction_count,
            "patient_data": patient_hero.patient_data.to_dict(),
            "session_status": patient_hero.get_patient_status(),
            "wandb_tracking": {
                "interactions_logged": interaction_count,
                "guardrail_events": "tracked_per_interaction",
                "conversation_flow": "full_history_available"
            }
        }
        
    except Exception as e:
        print(f"Error in session summary: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    # Check if running in development mode
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"Starting PatientHero CrewAI API server on {host}:{port}")
    print(f"API Documentation: http://{host}:{port}/docs")
    print(f"Frontend should connect to: http://{host}:{port}/api/chat")
    
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=True,  # Enable auto-reload in development
        log_level="info"
    )
