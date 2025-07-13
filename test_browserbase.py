import os
import asyncio
import json
import openai
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai.api_key = os.getenv('OPENAI_API_KEY')

async def extract_appointment_slots(page):
    """Directly extract appointment slots from the booking section."""
    try:
        print("\nLooking for appointment slots in the booking section...")
        
        # Take a screenshot of the full page for debugging
        await page.screenshot(path='debug_full_page.png')
        print("Saved full page screenshot as 'debug_full_page.png'")
        
        # Try multiple selectors that might contain the booking section
        booking_selectors = [
            'div[data-testid="book-appointment"]',  # Common test ID pattern
            'div.appointment-widget',                # Common class name
            'section.appointment',                   # Another common pattern
            'div.booking-container',                 # Generic container
            'div[class*="appointment"]',            # Any element with appointment in class
            'div[class*="booking"]',                # Any element with booking in class
            'button:has-text("Book Appointment")',  # Button that might be near the booking section
            'a:has-text("Book Appointment")'        # Link that might be near the booking section
        ]
        
        # Try each selector until we find the booking section
        booking_section = None
        for selector in booking_selectors:
            try:
                print(f"Trying selector: {selector}")
                booking_section = await page.wait_for_selector(selector, timeout=5000)
                if booking_section:
                    print(f"Found booking section with selector: {selector}")
                    break
            except Exception as e:
                print(f"Selector {selector} not found")
                continue
                
        if not booking_section:
            print("Could not find booking section with any selector")
            return []
            
        # Take a screenshot of just the booking section
        await booking_section.screenshot(path='booking_section.png')
        print("Saved booking section screenshot as 'booking_section.png'")
        
        # Extract all time slots with more specific targeting
        time_slots = await page.evaluate('''(selector) => {
            const slots = [];
            const bookingSection = document.querySelector(selector);
            if (!bookingSection) return [];
            
            // First, try to find time slot buttons in the booking section
            const timeSlotSelectors = [
                'button[data-testid*="time-slot"]',  // Common test ID pattern
                'button[class*="time-slot"]',       // Common class pattern
                'div[class*="time-slot"] button',    // Button inside time slot div
                'div[class*="appointment-slot"]',    // Appointment slot div
                'button[class*="appointment"]',      // Any appointment button
                'button:has-text("AM"), button:has-text("PM")',  // Buttons with AM/PM
                'div[class*="time"]',                // Any div with time in class
                'button[class*="time"]'              // Any button with time in class
            ];
            
            // Try each selector until we find time slots
            let slotElements = [];
            for (const sel of timeSlotSelectors) {
                const elements = bookingSection.querySelectorAll(sel);
                if (elements.length > 0) {
                    slotElements = Array.from(elements);
                    console.log(`Found ${slotElements.length} elements with selector: ${sel}`);
                    break;
                }
            }
            
            // If no specific slot elements found, get all buttons and divs in the booking section
            if (slotElements.length === 0) {
                slotElements = Array.from(bookingSection.querySelectorAll('button, div'));
                console.log(`No specific slot elements found, checking all ${slotElements.length} buttons and divs`);
            }
            
            // Process all potential slot elements
            slotElements.forEach(slot => {
                const text = slot.innerText.trim();
                // Look for time patterns like 9:00 AM or 2:30 PM
                const timeMatch = text.match(/(\d{1,2}:?\d{0,2}\s*[AP]M?)/i);
                if (timeMatch) {
                    const timeStr = timeMatch[1];
                    // Get parent element for additional context
                    const parentText = slot.parentElement ? 
                        slot.parentElement.innerText.trim().substring(0, 100) : '';
                        
                    slots.push({
                        time: timeStr,
                        element_text: text,
                        parent_text: parentText,
                        available: !slot.disabled && !slot.getAttribute('aria-disabled') && 
                                 !slot.classList.contains('unavailable') &&
                                 !slot.classList.contains('disabled') &&
                                 !slot.classList.contains('full'),
                        tag_name: slot.tagName,
                        class_list: Array.from(slot.classList).join(' ')
                    });
                }
            });
            
            // If still no slots, try to extract from the booking section text
            if (slots.length === 0) {
                const sectionText = bookingSection.innerText;
                // Look for time patterns in the text
                const timeRegex = /(\d{1,2}:?\d{0,2}\s*[AP]M?)/gi;
                const matches = sectionText.matchAll(timeRegex);
                const uniqueTimes = new Set();
                
                for (const match of matches) {
                    uniqueTimes.add(match[0]);
                }
                
                if (uniqueTimes.size > 0) {
                    return Array.from(uniqueTimes).map(time => ({
                        time: time,
                        status: 'available',
                        source: 'text_extraction',
                        element_text: `Found in text: ${time}`
                    }));
                }
                
                // If we still have nothing, return the first 200 chars of the section text
                return [{
                    status: 'available',
                    details: 'Appointment booking available',
                    element_text: sectionText.substring(0, 200) + (sectionText.length > 200 ? '...' : '')
                }];
            }
            
            return slots.length > 0 ? slots : [];
        }''', selector)
        
        if time_slots and len(time_slots) > 0:
            print(f"Found {len(time_slots)} time slots")
            
            # Add metadata to each slot
            current_date = datetime.now().strftime("%Y-%m-%d")
            for slot in time_slots:
                if 'date' not in slot:
                    slot['date'] = current_date
                if 'type' not in slot:
                    slot['type'] = 'New Patient Visit'
                if 'status' not in slot:
                    slot['status'] = 'available' if slot.get('available', True) else 'unavailable'
                
                # Clean up the time format if needed
                if 'time' in slot:
                    slot['time'] = slot['time'].replace(' ', '').upper()
                    
            return time_slots
            
        return []
        
        
    except Exception as e:
        print(f"Error extracting appointment slots: {str(e)}")
        return []

async def extract_appointments_with_openai(page_content):
    """Fallback method using OpenAI to extract appointment information."""
    try:
        # Get the visible text from the page
        soup = BeautifulSoup(page_content, 'html.parser')
        
        # Remove unwanted elements that might confuse the AI
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()
            
        # Get all text content with some structure
        content_blocks = []
        for element in soup.find_all(['div', 'section', 'article', 'main', 'form'], recursive=True):
            text = element.get_text(' ', strip=True)
            if 20 < len(text) < 1000:  # Filter out too short or too long blocks
                content_blocks.append(text)
        
        # Combine the most relevant sections
        visible_text = "\n---\n".join(content_blocks[:20])  # Limit to top 20 sections
        
        # Create a more detailed prompt with examples
        prompt = f"""Extract any available appointment time slots from the following content. 
        Look for available times, appointment slots, or booking information.
        
        Content to analyze:
        {visible_text}
        
        Return a JSON array of appointment objects. If no appointments are found, return an empty array [].
        
        Example output:
        [
            {{
                "time": "10:30 AM",
                "date": "2023-07-15",
                "type": "New Patient Visit",
                "status": "available"
            }}
        ]"""
        
        # Call OpenAI API with more specific instructions
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an AI specialized in extracting healthcare appointment information. "
                                 "Be precise and only return actual available appointment times."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
        )
        
        # Parse the response
        content = response.choices[0].message.content
        
        # Clean up the response to get just the JSON
        try:
            # Try to find JSON in the response
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1].split('```')[0]
                
            # Parse the JSON
            appointments = json.loads(content)
            return appointments
            
        except json.JSONDecodeError:
            print("Error parsing OpenAI response as JSON. Raw response:", content)
            return []
            
    except Exception as e:
        print(f"Error in extract_appointments_with_openai: {str(e)}")
        return []

async def extract_appointment_times(page, booking_url):
    """Extract available appointment times from the booking page."""
    try:
        print(f"\nNavigating to booking page: {booking_url}")
        
        # Navigate to the booking page
        if not booking_url.startswith('http'):
            booking_url = 'https://www.oakstreethealth.com' + booking_url
        
        await page.goto(booking_url, wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")
        
        # Wait for the appointment calendar to load
        try:
            # Wait for the calendar container or time slots to be visible
            await page.wait_for_selector('.calendar-container, .time-slot, [data-testid*="time-slot"]', 
                                       state='visible', timeout=10000)
            
            # Take a screenshot of the booking page
            await page.screenshot(path='booking_page.png')
            print("Screenshot of booking page saved as booking_page.png")
            
            # Extract available dates and times
            print("\nExtracting available appointment times...")
            
            # Try different selectors that might contain appointment times
            selectors = [
                '.time-slot',
                '[data-testid*="time-slot"]',
                '.appointment-time',
                '.slot-available',
                '.time-button',
                'button[data-time]'
            ]
            
            available_times = []
            
            for selector in selectors:
                time_elements = await page.query_selector_all(selector)
                if time_elements:
                    for element in time_elements:
                        try:
                            # Get the time text and any associated date
                            time_text = await element.inner_text()
                            date_text = ''
                            
                            # Try to find a parent element that might contain the date
                            parent = await element.query_selector('xpath=./ancestor::div[contains(@class, "date") or contains(@class, "day")]')
                            if parent:
                                date_text = await parent.inner_text()
                                date_text = ' '.join(date_text.split()[:3])  # Get just the date part
                            
                            if time_text.strip() and 'am' in time_text.lower() or 'pm' in time_text.lower():
                                available_times.append(f"{date_text}: {time_text.strip()}")
                        except Exception as e:
                            continue
                    
                    if available_times:
                        break
            
            if available_times:
                print("\nFound available appointment times:")
                for time_slot in available_times:
                    print(f"- {time_slot}")
                return available_times
            else:
                print("No available appointment times found using standard selectors.")
                
                # Try a more aggressive approach to find any time-like text
                page_text = await page.content()
                soup = BeautifulSoup(page_text, 'html.parser')
                
                # Look for time patterns like 9:00 AM or 2:30 PM
                import re
                time_pattern = re.compile(r'\b(1[0-2]|0?[1-9]):[0-5][0-9]\s?(?:AM|PM|am|pm)\b')
                potential_times = soup.find_all(text=time_pattern)
                
                if potential_times:
                    print("\nFound potential time slots (may include non-selectable times):")
                    for time in set([t.strip() for t in potential_times if t.strip()]):
                        print(f"- {time}")
                    return list(set([t.strip() for t in potential_times if t.strip()]))
                else:
                    print("Could not find any time slots on the page.")
                    return []
                    
        except Exception as e:
            print(f"Error finding appointment times: {str(e)}")
            return []
            
    except Exception as e:
        print(f"Error navigating to booking page: {str(e)}")
        return []

async def search_with_zip_code(page, zip_code="77065"):
    """Search for appointments using ZIP code."""
    print(f"\nAttempting to search with ZIP code: {zip_code}")
    
    # Common selectors for ZIP code search
    zip_selectors = [
        'input[placeholder*="ZIP" i], input[placeholder*="Zip" i]',
        'input[name*="zip" i], input[id*="zip" i]',
        'input[type="text"], input[type="number"]',
        'input',
    ]
    
    # Common selectors for search/submit buttons
    button_selectors = [
        'button:has-text("Search")',
        'button:has-text("Find")',
        'button:has-text("Book")',
        'button[type="submit"]',
        'button',
        'input[type="submit"]',
    ]
    
    try:
        # Try to find and fill ZIP code field
        zip_filled = False
        for selector in zip_selectors:
            try:
                zip_field = await page.wait_for_selector(selector, timeout=5000)
                if zip_field:
                    await zip_field.fill(zip_code)
                    print(f"Filled ZIP code: {zip_code}")
                    zip_filled = True
                    break
            except:
                continue
        
        if not zip_filled:
            print("Could not find ZIP code field. Taking a screenshot for debugging.")
            await page.screenshot(path='zip_search_failed.png')
            return False
        
        # Try to find and click search/submit button
        for selector in button_selectors:
            try:
                button = await page.query_selector(selector)
                if button and await button.is_visible():
                    await button.click()
                    print("Clicked search/submit button")
                    await page.wait_for_load_state("networkidle")
                    return True
            except:
                continue
        
        # If no button was clicked, try pressing Enter
        await page.keyboard.press('Enter')
        print("Pressing Enter to submit form")
        await page.wait_for_load_state("networkidle")
        return True
        
    except Exception as e:
        print(f"Error during ZIP code search: {str(e)}")
        return False

async def test_website_for_appointments(url):
    """Test a website for appointment booking functionality using Playwright."""
    print(f"\nTesting website: {url}")
    
    # Launch Playwright browser
    async with async_playwright() as p:
        # Launch browser (set headless=False to see the browser)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        page = await context.new_page()
        
        try:
            # Navigate to the URL
            print(f"Navigating to: {url}")
            response = await page.goto(url, wait_until="domcontentloaded")
            
            # Wait for the page to load
            await page.wait_for_load_state("networkidle")
            
            # Get page title and URL
            page_title = await page.title()
            current_url = page.url
            print(f"Page title: {page_title}")
            print(f"Current URL: {current_url}")
            
            # First, check if there are any available appointments on the landing page
            print("\nChecking for available appointments on the landing page...")
            
            # Look for common appointment availability indicators
            availability_keywords = [
                'available', 'book now', 'schedule now', 'appointments available',
                'next available', 'same day', 'open slots', 'slots available'
            ]
            
            # Check for any elements containing availability keywords
            found_availability = False
            for keyword in availability_keywords:
                elements = await page.query_selector_all(f':text-matches("{keyword}", "i")')
                if elements:
                    for element in elements:
                        try:
                            text = await element.inner_text()
                            if len(text) < 100:  # Filter out large blocks of text
                                print(f"Found availability indicator: {text.strip()}")
                                found_availability = True
                        except:
                            continue
            
            if found_availability:
                print("\nAppointments appear to be available on the landing page!")
                await page.screenshot(path='appointments_available.png')
                print("Screenshot saved as 'appointments_available.png'")
                
                # First try direct extraction of time slots
                print("\nAttempting to extract appointment slots directly...")
                appointments = await extract_appointment_slots(page)
                
                # If no slots found, fall back to OpenAI
                if not appointments:
                    print("No slots found with direct extraction, trying OpenAI...")
                    page_content = await page.content()
                    appointments = await extract_appointments_with_openai(page_content)
                
                if appointments:
                    print("\n=== Extracted Appointment Slots ===")
                    for i, appt in enumerate(appointments, 1):
                        print(f"\nSlot {i}:")
                        for key, value in appt.items():
                            if key != 'element_text' or len(str(value)) < 100:  # Don't print very long text
                                print(f"  {key}: {value}")
                    
                    # Save to JSON file
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_file = f'appointments_{timestamp}.json'
                    with open(output_file, 'w') as f:
                        json.dump(appointments, f, indent=2)
                    print(f"\nAppointments saved to {output_file}")
                else:
                    print("No appointment slots could be found on the page.")
                    # Take a screenshot for debugging
                    await page.screenshot(path='no_slots_found.png')
                    print("Saved screenshot as 'no_slots_found.png' for debugging")
                
                return
                
            print("No immediate appointment availability found on the landing page.")
            
            # If no availability found, look for booking/search functionality
            print("\nLooking for booking/search functionality...")
            
            # Try to find and use a ZIP code search form
            print("Attempting to search with ZIP code 77065...")
            search_success = await search_with_zip_code(page, "77065")
            
            if search_success:
                print("\nSearch completed. Checking for available appointments...")
                
                # Take a screenshot of the search results
                await page.screenshot(path='search_results.png')
                print("Search results screenshot saved as 'search_results.png'")
                
                # Look for available time slots
                time_selectors = [
                    '.time-slot',
                    '.appointment-time',
                    '.slot-available',
                    '.time-button',
                    'button[data-time]',
                    ':text-matches("AM"):not(script)',
                    ':text-matches("PM"):not(script)'
                ]
                
                found_times = []
                for selector in time_selectors:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        try:
                            text = await element.inner_text()
                            if any(x in text.upper() for x in ['AM', 'PM']) and len(text) < 20:
                                found_times.append(text.strip())
                        except:
                            continue
                
                if found_times:
                    print("\nFound available appointment times:")
                    for time in sorted(set(found_times)):  # Remove duplicates and sort
                        print(f"- {time}")
                    
                    # Get the full page content for OpenAI analysis
                    page_content = await page.content()
                    
                    # Extract appointments using OpenAI
                    print("\nExtracting structured appointment details using OpenAI...")
                    appointments = await extract_appointments_with_openai(page_content)
                    
                    if appointments:
                        print("\nStructured appointment slots:")
                        for appt in appointments:
                            print(f"- {appt.get('date', 'No date')} at {appt.get('time', 'no time')} "
                                  f"(Type: {appt.get('type', 'N/A')}, Location: {appt.get('location', 'N/A')})")
                        
                        # Save to JSON file
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        output_file = f'appointments_{timestamp}.json'
                        with open(output_file, 'w') as f:
                            json.dump(appointments, f, indent=2)
                        print(f"\nStructured appointments saved to {output_file}")
                    else:
                        print("No structured appointment data could be extracted.")
                        
                        # Save the raw page content for debugging
                        with open('search_results.html', 'w', encoding='utf-8') as f:
                            f.write(page_content)
                        print("Saved search results as 'search_results.html'")
                else:
                    print("\nNo available appointment times found in search results.")
                    
                    # Save the page content for debugging
                    page_content = await page.content()
                    with open('search_results.html', 'w', encoding='utf-8') as f:
                        f.write(page_content)
                    print("Saved search results as 'search_results.html'")
            
            # Take a final screenshot
            await page.screenshot(path='final_page.png')
            print("\nFinal page screenshot saved as 'final_page.png'")
            
        except Exception as e:
            print(f"Error during page processing: {str(e)}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Close the browser
            await browser.close()
            print("Browser closed.")

if __name__ == "__main__":
    # Test with Oak Street Health location
    test_url = "https://www.oakstreethealth.com/locations/houston-tx/cypress-doctors-office"
    print(f"Testing Oak Street Health location: {test_url}")
    asyncio.run(test_website_for_appointments(test_url))
