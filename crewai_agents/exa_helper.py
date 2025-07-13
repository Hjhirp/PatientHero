#!/usr/bin/env python3

"""
Exa Helper - Receives patient data from PatientHero CrewAI
This simulates an external medical system that would process patient intake data
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any
from dotenv import load_dotenv
from exa_py import Exa

# Load environment variables
load_dotenv()

class ExaHelper:
    """Medical system for fetching hospitals with .org or .gov domains only."""
    def __init__(self):
        self.processed_file = "./processed_medical_data.json"
        exa_api_key = os.getenv("EXA_API_KEY")
        if not exa_api_key:
            print("⚠️  Warning: EXA_API_KEY not found in environment variables")
            self.exa = None
        else:
            self.exa = Exa(api_key=exa_api_key)

    def process_patient_from_main(self, patient_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch and save hospitals with .org or .gov domains only, improved search and insurance check."""
        if not self.exa:
            print("Exa.ai not configured.")
            return []
        
        zip_code = patient_data.get('zip_code')
        medical_condition = patient_data.get('medical_condition')
        insurance = patient_data.get('insurance')
        
        # Improved search query for more relevant results
        search_query = f"best hospitals OR medical centers OR clinics for near {zip_code} site:.org OR site:.gov"
        result = self.exa.search_and_contents(
            search_query,
            text=True,
            num_results=15
        )
        hospitals = []
        for item in result.results:
            url = item.url
            if not (url.endswith('.org') or '.org/' in url or '.gov' in url):
                continue
            if not ('.org' in url or '.gov' in url):
                continue
            # Use Exa answer API to check insurance acceptance
            accepts_insurance = self._exa_check_insurance(item.title, insurance, url)
            hospital = {
                "hospital_name": item.title,
                "link": url,
                "institution_type": self._guess_institution_type(item.title, url),
                "accepts_user_insurance": accepts_insurance
            }
            hospitals.append(hospital)
            if len(hospitals) == 5:
                break
        with open(self.processed_file, 'w') as f:
            json.dump(hospitals, f, indent=2)
        print(f"💾 Saved {len(hospitals)} hospitals to {self.processed_file}")
        return hospitals

    def _guess_institution_type(self, title: str, url: str) -> str:
        title_lower = title.lower() if title else ''
        if 'emergency' in title_lower:
            return 'Emergency Room'
        if 'urgent' in title_lower:
            return 'Urgent Care'
        if 'hospital' in title_lower:
            return 'Hospital'
        if 'clinic' in title_lower:
            return 'Clinic'
        if 'medical center' in title_lower:
            return 'Medical Center'
        if 'va' in title_lower or 'veterans' in title_lower or '.gov' in url:
            return 'Government Facility'
        return 'Healthcare Facility'

    def _exa_check_insurance(self, hospital_name: str, insurance: str, url: str) -> str:
        """Use Exa answer API to check if insurance is accepted on the hospital's page."""
        if not insurance or not url or not self.exa:
            return "unknown"
        try:
            question = f"Does {hospital_name} accept {insurance}?"
            answer = self.exa.answer(question=question)    
            if answer and hasattr(answer, 'answer'):
                ans = answer.answer.lower()
                if 'yes' in ans or 'accept' in ans:
                    return "true"
                elif 'no' in ans or 'not accept' in ans:
                    return "false"
            return "unknown"
        except Exception:
            return "unknown"

if __name__ == "__main__":
    print("This module is designed to be imported and called from main.py or a test script.")
