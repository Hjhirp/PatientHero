#!/usr/bin/env python3
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

# Add the crewai_agents directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'crewai_agents'))

try:
    from main import PatientHeroCrewAI
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
        session_id = request.session_id
        
        # Get or create PatientHero instance for this session
        if session_id and session_id in patient_sessions:
            patient_hero = patient_sessions[session_id]
        else:
            patient_hero = PatientHeroCrewAI()
            session_id = patient_hero.patient_data.session_id
            patient_sessions[session_id] = patient_hero
        
        # Process user input through CrewAI
        response = patient_hero.process_user_input(request.user_input)
        
        return ChatResponse(
            agent=response['agent'],
            response=response['response'],
            patient_data=response['patient_data'],
            next_step=response['next_step'],
            extraction_data=response.get('extraction_data')
        )
        
    except Exception as e:
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
