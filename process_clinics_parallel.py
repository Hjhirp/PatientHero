#!/usr/bin/env python3
"""
Parallel Clinic Appointment Scraper

This script processes multiple clinic websites in parallel to extract appointment availability
and saves the results to a JSON file.
"""
import asyncio
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

# Constants
INPUT_FILE = 'test_clinic_list.json'
OUTPUT_FILE = 'test_clinic_list_with_appts.json'
MAX_CONCURRENT_TASKS = 5  # Limit concurrent browser instances to avoid rate limiting
REQUEST_TIMEOUT = 60000  # 60 seconds timeout for each page

# Global browser instance to be shared across tasks
browser = None

class ClinicProcessor:
    """Handles processing of individual clinic websites."""
    
    @staticmethod
    async def extract_appointment_slots(page) -> List[Dict[str, Any]]:
        """Extract appointment slots from the booking section."""
        try:
            # Wait for potential dynamic content to load
            await page.wait_for_load_state('networkidle')
            
            # Take a screenshot for debugging
            timestamp = int(time.time())
            os.makedirs('screenshots', exist_ok=True)
            screenshot_path = f'screenshots/appointments_{timestamp}.png'
            await page.screenshot(path=screenshot_path)
            
            # Try to extract slots using multiple approaches
            slots = await page.evaluate('''() => {
                const results = [];
                
                // Function to check if element is visible
                const isVisible = (elem) => {
                    if (!elem) return false;
                    const style = window.getComputedStyle(elem);
                    return style.display !== 'none' && 
                           style.visibility !== 'hidden' && 
                           style.opacity !== '0';
                };
                
                // Look for time slot buttons or links
                const timePattern = /(\d{1,2}:?\d{0,2}\s*[AP]M?)/i;
                const selectors = [
                    'button', 'a', 'div[role="button"]', 
                    'div[class*="time"]', 'div[class*="slot"]',
                    'button[class*="time"]', 'a[class*="time"]',
                    'button[class*="appointment"]', 'a[class*="appointment"]',
                    'div[class*="appointment"]', 'div[class*="book"]'
                ];
                
                // Check all elements that might contain time slots
                for (const sel of selectors) {
                    const elements = document.querySelectorAll(sel);
                    for (const el of elements) {
                        if (!isVisible(el)) continue;
                        const text = el.innerText.trim();
                        if (timePattern.test(text)) {
                            results.push({
                                time: text,
                                element: el.outerHTML.substring(0, 100),
                                selector: sel,
                                source: 'direct_extraction'
                            });
                        }
                    }
                }
                
                // If no slots found, try to extract from page text
                if (results.length === 0) {
                    const text = document.body.innerText;
                    const timeRegex = /(\d{1,2}:?\d{0,2}\s*[AP]M?)/gi;
                    const matches = text.matchAll(timeRegex);
                    const uniqueTimes = new Set();
                    
                    for (const match of matches) {
                        uniqueTimes.add(match[0]);
                    }
                    
                    return Array.from(uniqueTimes).map(time => ({
                        time: time,
                        source: 'text_extraction',
                        element: 'N/A'
                    }));
                }
                
                return results;
            }''')
            
            return slots or []
            
        except Exception as e:
            print(f"Error extracting slots: {str(e)}")
            return []
    
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
            
            # Extract appointment slots
            print("  Extracting appointment slots...")
            slots = await cls.extract_appointment_slots(page)
            
            # Close the page and context
            await page.close()
            await context.close()
            
            # Prepare result
            result = {
                **clinic_data,
                'appointment_slots': slots,
                'last_checked': datetime.now().isoformat(),
                'status': 'success' if slots else 'no_slots_found'
            }
            
            print(f"  Found {len(slots)} appointment slots")
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


def load_clinics() -> Dict[str, List[Dict[str, Any]]]:
    """Load clinic data from the input JSON file."""
    try:
        with open(INPUT_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading clinics: {str(e)}")
        return {}


def save_results(clinics_data: Dict[str, List[Dict[str, Any]]]) -> None:
    """Save the processed results to the output JSON file."""
    try:
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(clinics_data, f, indent=2)
        print(f"\nResults saved to {OUTPUT_FILE}")
    except Exception as e:
        print(f"Error saving results: {str(e)}")


async def main():
    """Main function to run the script."""
    start_time = time.time()
    
    # Load clinic data
    print(f"Loading clinics from {INPUT_FILE}...")
    clinics_data = load_clinics()
    
    if not clinics_data:
        print("No clinic data found or error loading file.")
        return
    
    # Process each location group in the data
    for location, clinics in clinics_data.items():
        if location == 'metadata' or not isinstance(clinics, list):
            continue
            
        print(f"\nProcessing {len(clinics)} clinics in {location}...")
        
        # Process clinics in parallel
        processed_clinics = await process_clinics_parallel(clinics)
        
        # Update the data with processed results
        clinics_data[location] = processed_clinics
        
        # Save progress after each location
        save_results(clinics_data)
    
    # Calculate and print total time
    total_time = time.time() - start_time
    print(f"\nCompleted processing in {total_time:.2f} seconds")


if __name__ == "__main__":
    asyncio.run(main())
