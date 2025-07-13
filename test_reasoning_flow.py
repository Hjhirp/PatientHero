#!/usr/bin/env python3
"""
Test script to verify the reasoning flow with debug output
"""

import requests
import json
import time

API_BASE = "http://localhost:8000/api"

def test_reasoning_flow():
    """Test the complete flow from basic info to reasoning"""
    
    print("🧪 Testing PatientHero Reasoning Flow")
    print("=" * 50)
    
    # Start a new session
    session_id = "test_session_" + str(int(time.time()))
    
    # Test messages that should provide complete basic info
    test_messages = [
        "Hi, I have a severe headache and need help finding a doctor",
        "My zip code is 90210",
        "My phone number is 555-123-4567", 
        "I have Blue Cross Blue Shield insurance",
        "The headache is getting worse and I'm feeling nauseous"
    ]
    
    for i, message in enumerate(test_messages):
        print(f"\n🗣️  Message {i+1}: {message}")
        
        response = requests.post(
            f"{API_BASE}/chat",
            json={
                "user_input": message,
                "session_id": session_id
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"🤖 Agent: {data.get('agent', 'unknown')}")
            print(f"📝 Response: {data.get('response', '')[:100]}...")
            print(f"🔄 Next step: {data.get('next_step', 'unknown')}")
            
            # Check if we've reached reasoning
            if data.get('agent') == 'reasoning_agent':
                print("✅ SUCCESS: Reasoning agent activated!")
                break
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            break
        
        time.sleep(1)  # Brief pause between messages
    
    print("\n" + "=" * 50)
    print("🏁 Test completed")

if __name__ == "__main__":
    test_reasoning_flow()
