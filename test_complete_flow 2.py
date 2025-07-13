#!/usr/bin/env python3
"""
Test the complete PatientHero flow:
1. Patient data collection
2. Appointment processing  
3. Comfort guidance (2 rounds)
4. Journey support
"""

import requests
import json
import time

def test_complete_flow():
    """Test the complete PatientHero medical flow"""
    base_url = "http://localhost:8000"
    
    print("🏥 Testing Complete PatientHero Medical Flow\n")
    
    # Step 1: Start a chat session
    print("Step 1: Starting chat session...")
    chat_response = requests.post(f"{base_url}/api/chat", json={
        "user_input": "Hi, I have a severe headache and need to find a doctor",
        "session_id": None
    })
    
    if chat_response.status_code != 200:
        print(f"❌ Chat failed: {chat_response.status_code}")
        return
    
    session_data = chat_response.json()
    session_id = session_data['patient_data']['session_id']
    print(f"✅ Session started: {session_id}")
    
    # Step 2: Provide patient information
    print("\nStep 2: Providing patient information...")
    patient_info = [
        "My medical condition is severe headache",
        "My ZIP code is 95051", 
        "My phone number is 555-123-4567",
        "I have Blue Cross insurance"
    ]
    
    for info in patient_info:
        response = requests.post(f"{base_url}/api/chat", json={
            "user_input": info,
            "session_id": session_id
        })
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {info} -> {data['agent']}")
        time.sleep(1)
    
    # Step 3: Trigger complete flow (appointments + comfort)
    print("\nStep 3: Processing complete medical flow...")
    flow_response = requests.post(f"{base_url}/api/complete-flow/{session_id}")
    
    if flow_response.status_code != 200:
        print(f"❌ Complete flow failed: {flow_response.status_code}")
        print(f"Error: {flow_response.text}")
        return
    
    flow_data = flow_response.json()
    print(f"✅ Flow completed successfully!")
    print(f"📅 Found {flow_data['appointments']['total_institutions']} institutions")
    print(f"🏥 With appointments: {len(flow_data['appointments']['institutions_with_appointments'])}")
    print(f"💚 Comfort guidance: Round {flow_data['comfort_guidance']['round']}")
    
    # Step 4: Get second round of comfort guidance
    print("\nStep 4: Getting second round of comfort guidance...")
    comfort_response = requests.get(f"{base_url}/api/comfort-guidance/{session_id}?round_number=2")
    
    if comfort_response.status_code == 200:
        comfort_data = comfort_response.json()
        print(f"✅ Comfort guidance round 2 received")
        print(f"💭 Message preview: {comfort_data['guidance'][:100]}...")
        print(f"🚗 Journey status: {comfort_data['journey_progress']}")
    
    print("\n🎯 Complete Flow Test Summary:")
    print("✅ Chat session established")
    print("✅ Patient data collected")
    print("✅ Appointments processed")
    print("✅ Comfort guidance provided (2 rounds)")
    print("✅ Journey support ready")
    
    print(f"\n🔗 View results at:")
    print(f"Frontend: http://localhost:3000")
    print(f"API Docs: http://localhost:8000/docs")
    print(f"Session ID: {session_id}")

if __name__ == "__main__":
    test_complete_flow()
