#!/usr/bin/env python3

"""
Test script for the ExaHelper (.org/.gov hospitals only)
"""

from exa_helper import ExaHelper
from datetime import datetime

def test_exa_helper():
    """Test the ExaHelper (.org/.gov only)"""
    print("🧪 Testing ExaHelper (.org/.gov domains only)")
    print("=" * 60)
    
    # Create system instance
    system = ExaHelper()
    
    # Test patient data
    test_patient = {
        "medical_condition": "chest pain",
        "zip_code": "94301",
        "insurance": "Aetna",
        "phone_suffix": "1234",
        "session_id": "test-session-123",
        "timestamp": datetime.now().isoformat()
    }
    
    print("📋 Test patient data:")
    print(f"   Condition: {test_patient['medical_condition']}")
    print(f"   Location: {test_patient['zip_code']}")
    print(f"   Insurance: {test_patient['insurance']}")
    print()
    
    # Process patient
    hospitals = system.process_patient_from_main(test_patient)
    print(f"\n📄 Processing completed!")
    print(f"Found {len(hospitals)} .org/.gov hospitals:")
    for i, hospital in enumerate(hospitals, 1):
        print(f"  {i}. {hospital['hospital_name']}")
        print(f"     Link: {hospital['link']}")
        print(f"     Type: {hospital['institution_type']}")
        print(f"     Accepts user insurance: {hospital['accepts_user_insurance']}")

if __name__ == "__main__":
    test_exa_helper()
