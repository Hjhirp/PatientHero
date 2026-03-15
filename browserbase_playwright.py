#!/usr/bin/env python3
"""
Browserbase Playwright Example

This script demonstrates how to use Browserbase's Playwright integration
for web scraping with the PatientHero application.
"""
import os
from dotenv import load_dotenv
from browserbase import Browserbase
import asyncio
from playwright.async_api import async_playwright

# Load environment variables
load_dotenv()

# Browserbase configuration
BROWSERBASE_API_KEY = os.getenv('BROWSERBASE_API_KEY')
BROWSERBASE_PROJECT_ID = os.getenv('BROWSERBASE_PROJECT_ID')

def run_browserbase_example():
    """Run a simple example using Browserbase with Playwright."""
    if not BROWSERBASE_API_KEY or not BROWSERBASE_PROJECT_ID:
        print("Error: BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID must be set in .env")
        return

    # Initialize Browserbase client
    browserbase = Browserbase(api_key=BROWSERBASE_API_KEY)
    
    # Create a new browser session with Browserbase (synchronous)
    print("Creating new Browserbase session...")
    session = browserbase.sessions.create(
        project_id=BROWSERBASE_PROJECT_ID
    )
    
    try:
        # Debug: Print the session object structure
        print("Session object structure:")
        print(f"Type: {type(session)}")
        print(f"Dir: {dir(session)}")
        print(f"Session ID: {getattr(session, 'id', 'Not found')}")
        
        # Get the WebSocket URL from the session
        # Note: The actual attribute name might be different, so we'll try common ones
        ws_url = None
        for attr in ['ws_url', 'wsUrl', 'endpoint', 'browser_ws_url']:
            if hasattr(session, attr):
                ws_url = getattr(session, attr)
                break
        
        if not ws_url:
            # If we couldn't find the WebSocket URL, try to construct it
            if hasattr(session, 'host'):
                ws_url = f"wss://{session.host}/playwright/{session.id}"
            else:
                # Try to get the host from the API response
                response_data = session.__dict__.get('_response', {}) if hasattr(session, '__dict__') else {}
                host = response_data.get('host', 'api.browserbase.com')
                ws_url = f"wss://{host}/playwright/{session.id}"
        
        print(f"Using WebSocket URL: {ws_url}")
        
        # Example clinic URL to test
        test_url = "https://www.oakstreethealth.com/locations/houston-tx/cypress-doctors-office"
        
        # Use Playwright with Browserbase
        async def run_playwright():
            async with async_playwright() as playwright:
                # Launch browser with the WebSocket URL
                print(f"Connecting to browser with WebSocket: {ws_url}")
                browser = await playwright.chromium.connect_over_cdp(ws_url)
                context = await browser.new_context()
                
                # Set a longer default timeout
                context.set_default_timeout(30000)  # 30 seconds
                
                # Create a new page
                page = await context.new_page()
                
                # Navigate to the clinic page
                print(f"Navigating to {test_url}...")
                await page.goto(test_url, wait_until="domcontentloaded")
                
                # Take a screenshot for verification
                await page.screenshot(path="browserbase_screenshot.png")
                print("Screenshot saved as browserbase_screenshot.png")
                
                # Extract appointment information (example)
                print("Extracting appointment information...")
                
                # Wait for appointment elements to load
                try:
                    await page.wait_for_selector("button, a, [role='button']", timeout=10000)
                    
                    # Extract all time slots (this is a simplified example)
                    time_slots = await page.evaluate('''() => {
                        const slots = [];
                        // Look for common appointment time selectors
                        const elements = document.querySelectorAll('button, a, [role="button"], [class*="time"], [class*="slot"]');
                        elements.forEach(el => {
                            const text = el.textContent.trim();
                            if (text && /\d{1,2}:?\d{0,2}\s*[AP]M?/i.test(text)) {
                                slots.push({
                                    text: text,
                                    className: el.className || '',
                                    tagName: el.tagName
                                });
                            }
                        });
                        return slots;
                    }''')
                    
                    print("\nFound potential time slots:")
                    for i, slot in enumerate(time_slots[:10]):  # Show first 10 slots
                        print(f"{i+1}. {slot['text']} (element: {slot['tagName']}.{slot['className'].split(' ')[0]})")
                    
                except Exception as e:
                    print(f"Error extracting time slots: {str(e)}")
                
                # Get the page title and URL
                title = await page.title()
                url = page.url
                print(f"\nPage title: {title}")
                print(f"Current URL: {url}")
                
                # Close the browser
                await browser.close()
                
        # Run the async Playwright code
        try:
            asyncio.get_event_loop().run_until_complete(run_playwright())
        except Exception as e:
            print(f"Error in Playwright execution: {str(e)}")
            raise
            
    except Exception as e:
        print(f"Error during Browserbase session: {str(e)}")
        
    finally:
        # Always clean up the session (synchronous)
        if 'session' in locals():
            print("\nCleaning up Browserbase session...")
            try:
                # Try different methods to close the session
                if hasattr(browserbase.sessions, 'close'):
                    browserbase.sessions.close(session.id)
                elif hasattr(browserbase.sessions, 'terminate'):
                    browserbase.sessions.terminate(session.id)
                else:
                    # If no close method is available, log the session ID for manual cleanup
                    print(f"No close method found. Please manually close session ID: {session.id}")
                print("Session closed successfully.")
            except Exception as e:
                print(f"Error closing session: {str(e)}")
                print(f"Session ID for manual cleanup: {getattr(session, 'id', 'Not available')}")

if __name__ == "__main__":
    run_browserbase_example()
