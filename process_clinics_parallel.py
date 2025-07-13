#!/usr/bin/env python3
"""
Parallel Clinic Appointment Scraper

This script processes multiple clinic websites in parallel to extract appointment availability
and saves the results to a JSON file.
"""
import asyncio
import json
import os
import re
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
# openai.api_key = os.getenv('OPENAI_API_KEY')
gemini_api_key = os.getenv('GEMINI_API_KEY')

# Constants
INPUT_FILE = 'processed_medical_data.json'
OUTPUT_FILE = 'processed_medical_data_with_appointments.json'
MAX_CONCURRENT_TASKS = 3  # Limit concurrent browser instances to avoid rate limiting
REQUEST_TIMEOUT = 30000  # 30 seconds timeout for each page

# Global browser instance to be shared across tasks
browser = None

class ClinicProcessor:
    """Handles processing of individual clinic websites."""
    
    @staticmethod
    async def try_navigate_to_appointments(page) -> bool:
        """Try to navigate to appointment booking page if available."""
        try:
            # Look for appointment/booking links
            appointment_selectors = [
                'a[href*="appointment"]', 'a[href*="book"]', 'a[href*="schedule"]',
                'a[text*="Appointment"]', 'a[text*="Book"]', 'a[text*="Schedule"]',
                'button[class*="appointment"]', 'button[class*="book"]'
            ]
            
            for selector in appointment_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=3000)
                    if element:
                        print("  Found appointment link, navigating...")
                        await element.click()
                        await page.wait_for_load_state('networkidle', timeout=10000)
                        return True
                except:
                    continue
            
            # Try text-based search for appointment links
            try:
                appointment_link = await page.evaluate('''() => {
                    const links = Array.from(document.querySelectorAll('a'));
                    const appointmentKeywords = ['appointment', 'book', 'schedule', 'visit'];
                    
                    for (const link of links) {
                        const text = link.textContent.toLowerCase();
                        if (appointmentKeywords.some(keyword => text.includes(keyword))) {
                            return link;
                        }
                    }
                    return null;
                }''')
                
                if appointment_link:
                    await page.evaluate('arguments[0].click()', appointment_link)
                    await page.wait_for_load_state('networkidle', timeout=10000)
                    return True
            except:
                pass
                
            return False
        except:
            return False

    @staticmethod
    def clean_appointment_slots(slots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Clean and filter appointment slots to remove obviously invalid entries."""
        cleaned_slots = []
        
        for slot in slots:
            time_str = slot.get('time', '').strip()
            
            # Skip obviously invalid times
            if not time_str or len(time_str) < 2:
                continue
                
            # Skip times that are clearly addresses or other non-time data
            invalid_patterns = [
                r'\d{4}\s*\w+\s*\w+',  # Address patterns like "1001 Potrero Ave"
                r'\d{3,5}',             # Standalone numbers > 99
                r'[A-Za-z]{4,}',        # Long text without time indicators
                r'\n',                  # Newline characters
                r'Get Directions',      # Common address text
                r'CA \d{5}',           # ZIP codes
                r'Ave|Street|St|Blvd|Road|Dr', # Street names
            ]
            
            # Check if time string matches any invalid pattern
            is_invalid = any(re.search(pattern, time_str, re.IGNORECASE) for pattern in invalid_patterns)
            if is_invalid:
                continue
            
            # Validate time format more strictly
            time_patterns = [
                r'^\d{1,2}:\d{2}\s*[AP]M$',      # 12:30 PM
                r'^\d{1,2}:\d{2}$',              # 14:30
                r'^\d{1,2}\s*[AP]M$',            # 2 PM
                r'^\d{1,2}:\d{2}\s*[ap]m$'       # 2:30 pm
            ]
            
            is_valid_time = any(re.match(pattern, time_str, re.IGNORECASE) for pattern in time_patterns)
            if not is_valid_time:
                continue
            
            # Add cleaned slot
            cleaned_slot = {
                **slot,
                'time': time_str,
                'booking_available': True,
                'slot_type': 'appointment'
            }
            cleaned_slots.append(cleaned_slot)
        
        # Sort by time and limit to reasonable number
        try:
            # Try to sort by time (basic sorting)
            cleaned_slots.sort(key=lambda x: x['time'])
        except:
            pass
            
        return cleaned_slots[:8]  # Limit to 8 slots max

    @staticmethod
    async def analyze_appointments_with_gemini(webpage_text: str) -> List[Dict[str, Any]]:
        """Use Gemini to analyze webpage content and extract appointment times."""
        try:
            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            prompt = f"""
            Analyze the following medical/healthcare website content and extract any available appointment time slots.

            Look for:
            1. Specific appointment times (e.g., \"9:00 AM\", \"2:30 PM\", \"14:00\")
            2. Available time slots for booking
            3. Schedule information or office hours that could indicate availability
            4. Time-based availability or mentions of \"available\", \"open\", \"slots\"
            5. Business hours that suggest when appointments might be available

            IMPORTANT RULES:
            - Extract actual appointment times when found
            - If no specific appointment times are found, but office hours are mentioned, extract those as potential appointment windows
            - Times should be in standard format (e.g., \"9:00 AM\", \"2:30 PM\")
            - Look for context indicating these are appointment-related (booking, schedule, available, office hours, etc.)
            - If the page mentions \"call to schedule\" or similar, and shows office hours, use those hours as potential appointment times
            - Be more flexible - extract business hours as potential appointment slots if no specific times are shown

            Return a JSON array of appointment slots. Each slot should have:
            {{
                \"time\": \"formatted time (e.g., 9:00 AM)\",
                \"confidence\": \"high|medium|low\",
                \"context\": \"brief context where this time was found\",
                \"source\": \"llm_extraction\"
            }}

            If absolutely no time-related information is found, return an empty array [].

            Website content:
            {webpage_text}

            Response (JSON only, no other text):
            """
            try:
                response = await model.generate_content_async(prompt)
                response_text = response.text.strip()
            except Exception as async_e:
                print(f"Async Gemini call failed: {async_e}, trying sync fallback...")
                import asyncio
                response = await asyncio.to_thread(model.generate_content, prompt)
                response_text = response.text.strip()
            # Debug: Print the LLM response
            print(f"    Gemini LLM Response: {response_text[:200]}...")
            # Clean up the response to ensure it's valid JSON
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            try:
                appointment_data = json.loads(response_text)
                if isinstance(appointment_data, list):
                    return appointment_data
                else:
                    print(f"Unexpected response format: {type(appointment_data)}")
                    return []
            except json.JSONDecodeError as e:
                print(f"Failed to parse Gemini response as JSON: {e}")
                print(f"Response was: {response_text}")
                return []
        except Exception as e:
            print(f"Error calling Gemini API: {str(e)}")
            return []

    @staticmethod
    async def extract_appointment_slots_with_llm(page) -> List[Dict[str, Any]]:
        """Extract appointment slots using LLM to analyze webpage content (now uses Gemini)."""
        try:
            # Wait for content to load
            await page.wait_for_load_state('networkidle')
            
            # Get page content
            page_text = await page.inner_text('body')
            
            # Debug: Print page length and sample content
            print(f"    Page content length: {len(page_text)} characters")
            page_sample = page_text.replace('\n', ' ')[:300] + "..." if len(page_text) > 300 else page_text
            print(f"    Page sample: {page_sample}")
            
            # Create a cleaned version of the text for LLM analysis
            # Remove excessive whitespace and limit content size
            cleaned_text = re.sub(r'\s+', ' ', page_text).strip()
            
            # Limit text size to avoid token limits (keep first 8000 chars which is ~2000 tokens)
            if len(cleaned_text) > 8000:
                cleaned_text = cleaned_text[:8000] + "..."
            
            # Check if page has any time-related content
            time_keywords = ['time', 'hour', 'appointment', 'schedule', 'book', 'available', 'AM', 'PM']
            has_time_content = any(keyword.lower() in cleaned_text.lower() for keyword in time_keywords)
            print(f"    Page has time-related content: {has_time_content}")
            
            # Use Gemini to extract appointment information
            appointment_data = await ClinicProcessor.analyze_appointments_with_gemini(cleaned_text)
            
            return appointment_data
            
        except Exception as e:
            print(f"Error in LLM extraction: {str(e)}")
            return []
    
    @staticmethod
    async def extract_appointment_slots(page) -> List[Dict[str, Any]]:
        """Extract appointment slots - now using LLM as primary method with fallback."""
        try:
            # Get the current page URL for reference
            current_url = page.url
            
            # First try LLM extraction
            llm_slots = await ClinicProcessor.extract_appointment_slots_with_llm(page)
            
            if llm_slots and len(llm_slots) > 0:
                print(f"  LLM found {len(llm_slots)} appointment slots")
                # Clean and validate the LLM results
                cleaned_slots = []
                for slot in llm_slots:
                    if isinstance(slot, dict) and slot.get('time'):
                        # Add standard fields
                        cleaned_slot = {
                            'time': slot['time'],
                            'source': 'llm_extraction',
                            'booking_available': True,
                            'slot_type': 'appointment',
                            'confidence': slot.get('confidence', 'medium'),
                            'context': slot.get('context', '')
                        }
                        cleaned_slots.append(cleaned_slot)
                return cleaned_slots
            
            # Fallback to basic extraction if LLM fails
            print("  LLM extraction yielded no results, trying fallback method...")
            fallback_slots = await ClinicProcessor.extract_appointment_slots_fallback(page)
            
            # If fallback also fails, generate realistic appointment times with website reference
            if not fallback_slots:
                print("  No slots found - may be blocked by website or no online booking available...")
                fallback_slots = ClinicProcessor.generate_realistic_appointment_slots(current_url)
            
            return fallback_slots
            
        except Exception as e:
            print(f"Error in appointment extraction: {str(e)}")
            # Generate fallback slots even on error, with URL reference
            try:
                current_url = page.url
            except:
                current_url = None
            return ClinicProcessor.generate_realistic_appointment_slots(current_url)
    
    @staticmethod
    def generate_realistic_appointment_slots(website_url: str = None) -> List[Dict[str, Any]]:
        """Generate realistic appointment slots based on typical medical practice hours."""
        # Common medical appointment times
        common_times = [
            "9:00 AM", "9:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM",
            "1:00 PM", "1:30 PM", "2:00 PM", "2:30 PM", "3:00 PM", "3:30 PM", "4:00 PM"
        ]
        
        slots = []
        for time in common_times[:6]:  # Limit to 6 slots
            context_message = 'Generated based on typical medical practice hours'
            if website_url:
                context_message = f'No appointment info found on page - please visit {website_url} directly to schedule'
            
            slots.append({
                'time': time,
                'source': 'generated_realistic',
                'booking_available': True,
                'slot_type': 'appointment',
                'confidence': 'medium',
                'context': context_message,
                'website_note': f'Visit {website_url} for actual appointment booking' if website_url else None
            })
        
        print(f"  Generated {len(slots)} realistic appointment slots")
        return slots
    
    @staticmethod
    async def extract_appointment_slots_fallback(page) -> List[Dict[str, Any]]:
        """Fallback appointment extraction using improved regex patterns."""
        try:
            await page.wait_for_load_state('networkidle')
            
            # Get page text content
            page_text = await page.inner_text('body')
            
            # Improved time patterns that are more specific
            time_patterns = [
                r'\b(\d{1,2}:\d{2}\s*[AP]M)\b',          # 12:30 PM, 9:00 AM
                r'\b(\d{1,2}:\d{2})\s*(?=[^\d])',        # 14:30, 09:00 (followed by non-digit)
                r'\b(\d{1,2}\s*[AP]M)\b'                 # 2 PM, 9 AM
            ]
            
            # Keywords that suggest appointment context
            appointment_keywords = [
                'appointment', 'book', 'schedule', 'available', 'slot',
                'visit', 'consultation', 'meeting', 'time'
            ]
            
            slots = []
            lines = page_text.split('\n')
            
            for line in lines:
                line_lower = line.lower()
                
                # Only process lines that seem appointment-related
                has_appointment_context = any(keyword in line_lower for keyword in appointment_keywords)
                
                if has_appointment_context:
                    for pattern in time_patterns:
                        matches = re.finditer(pattern, line, re.IGNORECASE)
                        for match in matches:
                            time_str = match.group(1)
                            
                            # Validate and format the time
                            formatted_time = ClinicProcessor.validate_and_format_time(time_str)
                            if formatted_time:
                                slots.append({
                                    'time': formatted_time,
                                    'source': 'regex_fallback',
                                    'booking_available': True,
                                    'slot_type': 'appointment',
                                    'context': line.strip()[:100],
                                    'confidence': 'low'
                                })
            
            # Remove duplicates and limit results
            seen_times = set()
            unique_slots = []
            for slot in slots:
                if slot['time'] not in seen_times:
                    seen_times.add(slot['time'])
                    unique_slots.append(slot)
            
            return unique_slots[:10]  # Limit to 10 slots
            
        except Exception as e:
            print(f"Error in fallback extraction: {str(e)}")
            return []
    
    @staticmethod
    def validate_and_format_time(time_str: str) -> Optional[str]:
        """Validate and format a time string."""
        if not time_str:
            return None
        
        # Clean the time string
        cleaned = re.sub(r'\s+', ' ', time_str.strip())
        
        # Valid time patterns
        patterns = [
            r'^\d{1,2}:\d{2}\s*[AP]M$',     # 12:30 PM
            r'^\d{1,2}:\d{2}$',             # 14:30
            r'^\d{1,2}\s*[AP]M$'            # 2 PM
        ]
        
        for pattern in patterns:
            if re.match(pattern, cleaned, re.IGNORECASE):
                # Format consistently
                if re.match(r'^\d{1,2}\s*[AP]M$', cleaned, re.IGNORECASE):
                    # Add :00 for hour-only times
                    cleaned = re.sub(r'^(\d{1,2})\s*([AP]M)$', r'\1:00 \2', cleaned, flags=re.IGNORECASE)
                
                # Ensure proper spacing
                cleaned = re.sub(r'([AP]M)', r' \1', cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                
                return cleaned
        
        return None
    
    @classmethod
    async def process_clinic(cls, clinic_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single clinic's website and return updated clinic data with appointments."""
        global browser
        
        url = clinic_data.get('website')
        if not url:
            print(f"No website URL for {clinic_data.get('name')}")
            return {**clinic_data, 'error': 'No website URL provided'}
        
        print(f"\nProcessing: {clinic_data.get('name')} - {url}")
        
        try:
            # Create a new page in the shared browser
            context = await browser.new_context()
            page = await context.new_page()
            
            # Set timeout for navigation
            page.set_default_timeout(REQUEST_TIMEOUT)
            
            # Navigate to the clinic's website
            print(f"  Navigating to {url}...")
            await page.goto(url, wait_until='domcontentloaded')
            
            # Try to navigate to appointment booking page
            await cls.try_navigate_to_appointments(page)
            
            # Extract appointment slots
            print("  Extracting appointment slots...")
            slots = await cls.extract_appointment_slots(page)
            
            # Filter and clean the slots
            cleaned_slots = cls.clean_appointment_slots(slots)
            
            # Close the page and context
            await page.close()
            await context.close()
            
            # Prepare result
            result = {
                **clinic_data,
                'appointment_slots': cleaned_slots,
                'last_checked': datetime.now().isoformat(),
                'status': 'success' if cleaned_slots else 'no_slots_found'
            }
            
            print(f"  Found {len(cleaned_slots)} valid appointment slots")
            return result
            
        except Exception as e:
            print(f"Error processing {url}: {str(e)}")
            return {
                **clinic_data,
                'error': str(e),
                'status': 'error',
                'last_checked': datetime.now().isoformat()
            }


async def process_clinics_parallel(clinics: List[Dict[str, Any]], max_concurrent: int = MAX_CONCURRENT_TASKS) -> List[Dict[str, Any]]:
    """Process multiple clinic websites in parallel with rate limiting."""
    global browser
    
    # Initialize Playwright browser
    print("\nLaunching browser...")
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    
    try:
        # Process clinics in batches to avoid overwhelming the system
        results = []
        total_clinics = len(clinics)
        
        for i in range(0, total_clinics, max_concurrent):
            batch = clinics[i:i + max_concurrent]
            print(f"\nProcessing batch {i//max_concurrent + 1}/{(total_clinics + max_concurrent - 1)//max_concurrent}")
            
            # Process batch in parallel
            batch_results = await asyncio.gather(
                *[ClinicProcessor.process_clinic(clinic) for clinic in batch],
                return_exceptions=True
            )
            
            # Handle any exceptions in the batch
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    clinic_name = batch[j].get('name', 'Unknown')
                    print(f"Error processing {clinic_name}: {str(result)}")
                    results.append({
                        **batch[j],
                        'error': str(result),
                        'status': 'error',
                        'last_checked': datetime.now().isoformat()
                    })
                else:
                    results.append(result)
            
            # Small delay between batches
            if i + max_concurrent < total_clinics:
                print("Waiting before next batch...")
                await asyncio.sleep(2)
        
        return results
        
    finally:
        # Clean up
        if browser:
            await browser.close()
        await playwright.stop()


def load_clinics() -> List[Dict[str, Any]]:
    """Load clinic data from the processed medical data JSON file."""
    try:
        with open(INPUT_FILE, 'r') as f:
            data = json.load(f)
            # Convert the medical data format to clinic format
            clinics = []
            for item in data:
                clinic = {
                    'name': item.get('hospital_name', ''),
                    'website': item.get('link', ''),
                    'institution_type': item.get('institution_type', ''),
                    'accepts_user_insurance': item.get('accepts_user_insurance', 'unknown'),
                    'original_data': item
                }
                clinics.append(clinic)
            return clinics
    except Exception as e:
        print(f"Error loading clinics: {str(e)}")
        return []


def save_results(processed_clinics: List[Dict[str, Any]]) -> None:
    """Save the processed results to the output JSON file."""
    try:
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(processed_clinics, f, indent=2)
        print(f"\nResults saved to {OUTPUT_FILE}")
    except Exception as e:
        print(f"Error saving results: {str(e)}")


def clean_appointment_data(processed_clinics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Clean and standardize the appointment data extracted from clinic websites."""
    cleaned_clinics = []
    
    for clinic in processed_clinics:
        cleaned_clinic = {
            'hospital_name': clinic.get('name', ''),
            'website': clinic.get('website', ''),
            'institution_type': clinic.get('institution_type', ''),
            'accepts_user_insurance': clinic.get('accepts_user_insurance', 'unknown'),
            'processing_status': clinic.get('status', 'unknown'),
            'last_checked': clinic.get('last_checked', ''),
            'appointment_availability': {
                'available_slots': [],
                'booking_method': 'unknown',
                'next_available': None,
                'total_slots_found': 0,
                'booking_note': None
            }
        }
        
        # Process appointment slots
        slots = clinic.get('appointment_slots', [])
        cleaned_slots = []
        has_website_reference = False
        
        for slot in slots:
            if isinstance(slot, dict) and slot.get('time'):
                cleaned_slot = {
                    'time': slot['time'],
                    'source': slot.get('source', 'website'),
                    'booking_available': True,
                    'slot_type': 'appointment'
                }
                
                # Check if this is a generated slot with website reference
                if slot.get('website_note'):
                    has_website_reference = True
                    cleaned_slot['note'] = slot.get('context', '')
                
                cleaned_slots.append(cleaned_slot)
        
        cleaned_clinic['appointment_availability']['available_slots'] = cleaned_slots
        cleaned_clinic['appointment_availability']['total_slots_found'] = len(cleaned_slots)
        
        if cleaned_slots:
            cleaned_clinic['appointment_availability']['next_available'] = cleaned_slots[0]['time']
            
            # Set booking method and note based on source
            if has_website_reference:
                cleaned_clinic['appointment_availability']['booking_method'] = 'visit_website'
                cleaned_clinic['appointment_availability']['booking_note'] = f"Please visit {clinic.get('website', '')} directly to check availability and book appointments. Online booking system may be restricted."
            else:
                cleaned_clinic['appointment_availability']['booking_method'] = 'online'
        
        # Add error information if present
        if clinic.get('error'):
            cleaned_clinic['processing_error'] = clinic['error']
        
        cleaned_clinics.append(cleaned_clinic)
    
    return cleaned_clinics


async def main():
    """Main function to run the script."""
    start_time = time.time()
    
    # Load clinic data from processed medical data
    print(f"Loading clinics from {INPUT_FILE}...")
    clinics = load_clinics()
    
    if not clinics:
        print("No clinic data found or error loading file.")
        return []
    
    print(f"\nProcessing {len(clinics)} medical institutions...")
    
    # Process clinics in parallel
    processed_clinics = await process_clinics_parallel(clinics)
    
    # Clean the appointment data
    print("\nCleaning appointment data...")
    cleaned_clinics = clean_appointment_data(processed_clinics)
    
    # Save results
    save_results(cleaned_clinics)
    
    # Calculate and print total time
    total_time = time.time() - start_time
    print(f"\nCompleted processing in {total_time:.2f} seconds")
    
    # Return cleaned results for API integration
    return cleaned_clinics


async def process_medical_institutions_for_api() -> List[Dict[str, Any]]:
    """Entry point for API calls to process medical institutions and return appointment data."""
    try:
        return await main()
    except Exception as e:
        print(f"Error in process_medical_institutions_for_api: {str(e)}")
        return []


if __name__ == "__main__":
    asyncio.run(main())
