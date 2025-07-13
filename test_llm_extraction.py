#!/usr/bin/env python3
"""
Test script for LLM-based appointment extraction
"""
import asyncio
import json
import os
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_llm_extraction():
    """Test the LLM extraction with sample webpage content."""
    
    # Sample webpage content that mimics appointment booking pages
    sample_content = """
    Welcome to City Medical Center
    
    Our office hours are Monday through Friday, 8:00 AM to 5:00 PM.
    
    Available appointment times today:
    - 9:00 AM
    - 10:30 AM 
    - 2:00 PM
    - 3:30 PM
    - 4:15 PM
    
    To book an appointment, please call (555) 123-4567 or use our online booking system.
    
    Address: 123 Main Street, San Francisco, CA 94102
    
    Schedule your visit with Dr. Smith today!
    """
    
    try:
        client = openai.AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        prompt = f"""
        Analyze the following medical/healthcare website content and extract any available appointment time slots.
        
        Look for:
        1. Specific appointment times (e.g., "9:00 AM", "2:30 PM", "14:00")
        2. Available time slots for booking
        3. Schedule information
        4. Time-based availability
        
        IMPORTANT RULES:
        - Only extract actual appointment times, not addresses, phone numbers, or other data
        - Times should be in standard format (e.g., "9:00 AM", "2:30 PM")
        - Ignore timestamps, dates without times, and non-appointment related times
        - Look for context indicating these are appointment slots (booking, schedule, available, etc.)
        - Do NOT extract: addresses, phone numbers, ZIP codes, street names, directions
        
        Return a JSON array of appointment slots. Each slot should have:
        {{
            "time": "formatted time (e.g., 9:00 AM)",
            "confidence": "high|medium|low",
            "context": "brief context where this time was found",
            "source": "llm_extraction"
        }}
        
        If no appointment times are found, return an empty array [].
        
        Website content:
        {sample_content}
        
        Response (JSON only, no other text):
        """
        
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert at extracting appointment time slots from healthcare websites. Return only valid JSON. Never extract addresses, phone numbers, or non-time data."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.1
        )
        
        # Parse the response
        response_text = response.choices[0].message.content.strip()
        print("LLM Response:")
        print(response_text)
        
        # Clean up the response to ensure it's valid JSON
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        
        try:
            appointment_data = json.loads(response_text)
            print(f"\nParsed {len(appointment_data)} appointment slots:")
            for slot in appointment_data:
                print(f"  - {slot['time']} (confidence: {slot['confidence']})")
            return appointment_data
        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM response as JSON: {e}")
            return []
            
    except Exception as e:
        print(f"Error calling OpenAI API: {str(e)}")
        return []

if __name__ == "__main__":
    asyncio.run(test_llm_extraction())
