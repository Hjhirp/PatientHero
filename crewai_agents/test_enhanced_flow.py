#!/usr/bin/env python3

"""
Simple test script to test the enhanced data extraction flow
"""

import os
import sys
from dotenv import load_dotenv

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import PatientHeroCrewAI

# Load environment variables
load_dotenv()

def test_enhanced_extraction():
    """Test the enhanced extraction flow with data extraction agent"""
    print("🧪 Testing Enhanced Data Extraction Flow")
    print("=" * 50)
    
    # Initialize the system
    print("Initializing PatientHero CrewAI system...")
    patient_hero = PatientHeroCrewAI()
    
    print("\n✅ System initialized successfully!")
    print(f"Session ID: {patient_hero.patient_data.session_id}")
    
    test_inputs = [
        "Hi there!",
        "I have a terrible headache that won't go away",
        "My zip code is 90210", 
        "You can reach me at 555-123-4567",
        "I have Blue Cross insurance",
        "I also feel nauseous and dizzy"
    ]
    
    print("\n🎭 Testing conversation flow...")
    
    for i, user_input in enumerate(test_inputs, 1):
        print(f"\n--- Test Input {i} ---")
        print(f"Patient: {user_input}")
        
        try:
            response = patient_hero.process_user_input(user_input)
            print(f"\n{response['agent'].replace('_', ' ').title()}: {response['response'][:200]}...")
            print(f"Next Step: {response['next_step']}")
            
            # Show current patient data status
            print(f"\n📊 Current Patient Data:")
            print(f"  Medical Condition: {patient_hero.patient_data.medical_condition}")
            print(f"  ZIP Code: {patient_hero.patient_data.zip_code}")
            print(f"  Phone: {patient_hero.patient_data.phone_number}")
            print(f"  Insurance: {patient_hero.patient_data.insurance}")
            print(f"  Symptoms: {patient_hero.patient_data.symptoms}")
            print(f"  Basic Info Complete: {patient_hero.patient_data.is_basic_info_complete()}")
            
        except Exception as e:
            print(f"❌ Error processing input: {e}")
            break
        
        print("-" * 60)
    
    print("\n🎉 Test completed!")
    print(f"Final Status: {'✅ Success' if patient_hero.patient_data.is_basic_info_complete() else '⚠️  Incomplete'}")

if __name__ == "__main__":
    test_enhanced_extraction()
