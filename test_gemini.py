#!/usr/bin/env python3
"""
Test script to verify Gemini integration is working properly
"""
import asyncio
import json
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
gemini_api_key = os.getenv('GEMINI_API_KEY')

async def test_gemini_extraction():
    """Test Gemini with sample medical website content."""
    
    # Sample medical website content with appointment information
    test_content = """
    Welcome to City Medical Center
    
    Book Your Appointment Online
    
    Available appointment times this week:
    - Monday: 9:00 AM, 10:30 AM, 2:00 PM, 3:30 PM
    - Tuesday: 8:30 AM, 11:00 AM, 1:30 PM, 4:00 PM
    - Wednesday: 9:30 AM, 12:00 PM, 2:30 PM
    
    Office Hours: Monday-Friday 8:00 AM to 5:00 PM
    Saturday: 9:00 AM to 1:00 PM
    
    To schedule an appointment, call (555) 123-4567 or use our online booking system.
    """
    
    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        prompt = f"""
        Analyze the following medical/healthcare website content and extract any available appointment time slots.

        Look for:
        1. Specific appointment times (e.g., "9:00 AM", "2:30 PM", "14:00")
        2. Available time slots for booking
        3. Schedule information or office hours that could indicate availability

        Return a JSON array of appointment slots. Each slot should have:
        {{
            "time": "formatted time (e.g., 9:00 AM)",
            "confidence": "high|medium|low",
            "context": "brief context where this time was found",
            "source": "llm_extraction"
        }}

        If absolutely no time-related information is found, return an empty array [].

        Website content:
        {test_content}

        Response (JSON only, no other text):
        """
        
        print("Testing Gemini 2.5 Flash with sample medical content...")
        print(f"API Key configured: {'Yes' if gemini_api_key else 'No'}")
        print(f"Using model: models/gemini-2.5-flash")
        
        try:
            response = await model.generate_content_async(prompt)
            response_text = response.text.strip()
        except Exception as async_e:
            print(f"Async call failed: {async_e}, trying sync...")
            response = await asyncio.to_thread(model.generate_content, prompt)
            response_text = response.text.strip()
        
        print(f"\nGemini Response: {response_text}")
        
        # Clean up the response
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        
        try:
            appointment_data = json.loads(response_text)
            print(f"\nParsed JSON successfully: {len(appointment_data)} slots found")
            
            for i, slot in enumerate(appointment_data):
                print(f"Slot {i+1}: {slot.get('time')} - {slot.get('confidence')} confidence")
                print(f"  Context: {slot.get('context', 'N/A')}")
            
            return appointment_data
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse as JSON: {e}")
            print(f"Raw response: {response_text}")
            return []
            
    except Exception as e:
        print(f"Error testing Gemini: {str(e)}")
        return []

if __name__ == "__main__":
    result = asyncio.run(test_gemini_extraction())
    print(f"\nTest completed. Found {len(result)} appointment slots.")
