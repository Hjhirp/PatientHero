#!/usr/bin/env python3
"""
FastAPI backend server for PatientHero CrewAI integration
Provides REST API endpoints for the Next.js frontend
"""

import os
import sys
import uuid
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
            "/api/complete-flow/{session_id}",
            "/api/appointments/{session_id}",
            "/api/comfort-guidance/{session_id}",
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
            # Use provided session_id or generate new one
            if session_id:
                # Update the instance to use the requested session_id
                patient_hero.patient_data.session_id = session_id
                patient_hero.monitor.session_id = session_id
            else:
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

@app.post("/api/appointments/process")
async def process_appointments():
    """
    Process medical institutions to extract appointment availability
    """
    try:
        # Import the appointment processor
        import sys
        import os
        sys.path.append(os.path.dirname(__file__))
        from process_clinics_parallel import process_medical_institutions_for_api
        
        print("Starting appointment processing...")
        cleaned_appointments = await process_medical_institutions_for_api()
        
        return {
            "status": "success",
            "message": f"Processed {len(cleaned_appointments)} medical institutions",
            "institutions_with_appointments": cleaned_appointments,
            "processing_timestamp": json.dumps({"timestamp": str(os.times())})
        }
        
    except Exception as e:
        print(f"Error processing appointments: {e}")
        raise HTTPException(status_code=500, detail=f"Appointment processing failed: {str(e)}")

@app.get("/api/appointments/{session_id}")
async def get_appointment_results(session_id: str):
    """
    Get processed appointment data for a session
    """
    try:
        # Create session if it doesn't exist
        if session_id not in patient_sessions:
            print(f"Creating new session for appointment request: {session_id}")
            patient_hero = PatientHeroCrewAI()
            patient_hero.patient_data.session_id = session_id
            patient_hero.monitor.session_id = session_id
            patient_sessions[session_id] = patient_hero
        else:
            patient_hero = patient_sessions[session_id]
        
        # Check if appointment results are available
        if hasattr(patient_hero, 'appointment_results') and patient_hero.appointment_results:
            return {
                "status": "success",
                "session_id": session_id,
                "total_institutions": len(patient_hero.appointment_results),
                "institutions_with_appointments": patient_hero.appointment_results,
                "processing_complete": True,
                "patient_data": patient_hero.patient_data.to_dict()
            }
        else:
            # Try to load from file if not in memory
            try:
                with open('processed_medical_data_with_appointments.json', 'r') as f:
                    appointment_data = json.load(f)
                return {
                    "status": "success",
                    "session_id": session_id,
                    "total_institutions": len(appointment_data),
                    "institutions_with_appointments": appointment_data,
                    "processing_complete": True,
                    "patient_data": patient_hero.patient_data.to_dict(),
                    "source": "file_system"
                }
            except FileNotFoundError:
                return {
                    "status": "pending",
                    "session_id": session_id,
                    "message": "Appointment processing not yet complete",
                    "processing_complete": False
                }
        
    except Exception as e:
        print(f"Error retrieving appointments: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve appointments: {str(e)}")

@app.get("/api/comfort-guidance/{session_id}")
async def comfort_guidance_rounds(session_id: str, round_number: int = 1):
    """
    Provide comfort and guidance during travel to hospital (2 rounds)
    """
    try:
        # Create session if it doesn't exist
        if session_id not in patient_sessions:
            print(f"Creating new session for comfort guidance: {session_id}")
            patient_hero = PatientHeroCrewAI()
            patient_hero.patient_data.session_id = session_id
            patient_hero.monitor.session_id = session_id
            patient_sessions[session_id] = patient_hero
        else:
            patient_hero = patient_sessions[session_id]
        
        # Comfort guidance prompts for different rounds
        comfort_prompts = {
            1: "The user is on their way to the hospital. Provide comforting, reassuring guidance about what to expect and how to stay calm during the journey. Keep it supportive and practical.",
            2: "This is the second round of comfort. The user is getting closer to the hospital. Provide encouraging words, remind them they're making the right choice, and offer specific tips for when they arrive at the hospital."
        }
        
        if round_number not in comfort_prompts:
            round_number = 1
        
        # Process comfort guidance through reasoning agent
        comfort_response = patient_hero.process_user_input(comfort_prompts[round_number])
        
        return {
            "session_id": session_id,
            "round": round_number,
            "guidance": comfort_response['response'],
            "agent": comfort_response['agent'],
            "next_round": round_number + 1 if round_number < 2 else None,
            "journey_progress": "en_route" if round_number == 1 else "arriving_soon"
        }
        
    except Exception as e:
        print(f"Error in comfort guidance: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/complete-flow/{session_id}")
async def complete_medical_flow(session_id: str):
    """
    Complete the full medical flow: process appointments + provide comfort guidance
    """
    try:
        # Validate session_id
        if not session_id or session_id.strip() == '' or session_id == 'undefined':
            session_id = f"auto-generated-{uuid.uuid4()}"
            print(f"Generated new session ID: {session_id}")
        
        # Create session if it doesn't exist
        if session_id not in patient_sessions:
            print(f"Creating new session for ID: {session_id}")
            patient_hero = PatientHeroCrewAI()
            patient_hero.patient_data.session_id = session_id
            patient_hero.monitor.session_id = session_id
            patient_sessions[session_id] = patient_hero
        else:
            patient_hero = patient_sessions[session_id]
        
        # Step 1: Process appointments from medical data
        print("Step 1: Processing appointments...")
        from process_clinics_parallel import process_medical_institutions_for_api
        appointments = await process_medical_institutions_for_api()
        
        # Step 2: Get first round of comfort guidance
        print("Step 2: Providing comfort guidance...")
        comfort_prompt = "The user has their appointment information and is preparing to go to the hospital. Provide reassuring, supportive guidance about the journey ahead and what to expect."
        
        comfort_response = patient_hero.process_user_input(comfort_prompt)
        
        return {
            "session_id": session_id,
            "flow_status": "completed",
            "appointments": {
                "total_institutions": len(appointments),
                "institutions_with_appointments": [apt for apt in appointments if apt.get('appointment_availability', {}).get('total_slots_found', 0) > 0],
                "next_steps": "Review appointments and select preferred institution"
            },
            "comfort_guidance": {
                "round": 1,
                "message": comfort_response['response'],
                "agent": comfort_response['agent'],
                "next_guidance_available": True
            },
            "recommendations": {
                "immediate_action": "Review available appointments and book the most suitable one",
                "journey_prep": "Prepare insurance information and patient ID",
                "comfort_support": "Access round 2 guidance when ready to travel"
            }
        }
        
    except Exception as e:
        print(f"Error in complete flow: {e}")
        raise HTTPException(status_code=500, detail=f"Complete flow failed: {str(e)}")

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
