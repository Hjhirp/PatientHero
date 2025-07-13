#!/usr/bin/env python3
"""
Appointment Data Cleaner

This script cleans and formats appointment data using OpenAI's API to extract
and normalize appointment times into a consistent format.
"""
import json
import os
import openai
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

# Constants
INPUT_FILE = 'test_clinic_list_with_appts.json'
OUTPUT_FILE = 'cleaned_clinic_appointments.json'

SYSTEM_PROMPT = """You are a helpful assistant that processes healthcare appointment data. 
Extract and normalize the appointment dates and times from the given data. 
For each clinic, return a clean, consistent list of available appointment slots with both date and time.

If the data seems to contain errors or no valid appointment times, return an empty list.

For each appointment, include both the date and time in a structured format.
Output only a JSON array of objects with 'date' and 'time' fields.

Example: [
    {"date": "2025-08-08", "time": "9:00 AM"},
    {"date": "2025-08-09", "time": "10:30 AM"},
    {"date": "2025-08-10", "time": "1:15 PM"}
]
"""

def clean_appointment_data(clinic_data: Dict[str, Any]) -> Dict[str, Any]:
    """Clean and format appointment data for a single clinic."""
    from datetime import datetime
    
    # Skip if no appointment slots or error in data
    if not clinic_data.get('appointment_slots') or clinic_data.get('status') == 'error':
        return {
            'name': clinic_data.get('name', ''),
            'address': clinic_data.get('address', ''),
            'telephone': clinic_data.get('phone', ''),
            'appointments_available': [],
            'last_updated': datetime.now().isoformat()
        }
    
    # Prepare the prompt for OpenAI
    prompt = f"""Extract and normalize the available appointment times from this clinic data:
    
    Clinic Name: {clinic_data.get('name')}
    Raw Appointment Slots: {json.dumps(clinic_data.get('appointment_slots', []), indent=2)}
    """
    
    try:
        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        # Parse the response and ensure it's in the correct format
        cleaned_times = json.loads(response.choices[0].message.content)
        
        # Validate the structure
        if cleaned_times and isinstance(cleaned_times, list):
            # Ensure each item has both date and time
            cleaned_times = [
                slot for slot in cleaned_times 
                if isinstance(slot, dict) and 'date' in slot and 'time' in slot
            ]
        
    except Exception as e:
        print(f"Error processing {clinic_data.get('name')}: {str(e)}")
        cleaned_times = []
    
    # Return the cleaned data in the requested format
    return {
        'name': clinic_data.get('name', ''),
        'address': clinic_data.get('address', ''),
        'telephone': clinic_data.get('phone', ''),
        'appointments_available': cleaned_times if isinstance(cleaned_times, list) else [],
        'last_updated': datetime.now().isoformat()
    }

def main():
    """Main function to process all clinic data."""
    print(f"Loading data from {INPUT_FILE}...")
    
    try:
        with open(INPUT_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading input file: {str(e)}")
        return
    
    # Process each location group
    results = {}
    for location, clinics in data.items():
        if location == 'metadata' or not isinstance(clinics, list):
            results[location] = clinics
            continue
            
        print(f"\nProcessing {len(clinics)} clinics in {location}...")
        cleaned_clinics = []
        
        for clinic in clinics:
            print(f"  Cleaning data for {clinic.get('name')}...")
            cleaned_clinic = clean_appointment_data(clinic)
            cleaned_clinics.append(cleaned_clinic)
        
        results[location] = cleaned_clinics
    
    # Save the cleaned data
    try:
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nCleaned data saved to {OUTPUT_FILE}")
    except Exception as e:
        print(f"Error saving results: {str(e)}")

if __name__ == "__main__":
    main()
