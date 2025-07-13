"""
Clinic Appointment Scraper using CrewAI and BrowserBase

This script reads a list of clinics from a JSON file, creates a CrewAI agent for each clinic,
and uses BrowserBase to scrape appointment availability information from each clinic's website.
"""
import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from dotenv import load_dotenv

# Import Crew AI and LLM components
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI

# Import BrowserBase
from browserbase import Browserbase

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
INPUT_JSON = "test_clinic_list.json"
OUTPUT_JSON = "test_clinic_list_with_appts.json"
BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY")
BROWSERBASE_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID")
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not BROWSERBASE_API_KEY or not BROWSERBASE_PROJECT_ID or not OPENAI_API_KEY:
    raise ValueError("Missing required environment variables: BROWSERBASE_API_KEY, BROWSERBASE_PROJECT_ID and OPENAI_API_KEY")

class ClinicScraper:
    """Handles the scraping of clinic websites for appointment availability."""
    
    def __init__(self):
        """Initialize the scraper with BrowserBase client."""
        self.browserbase_client = Browserbase(api_key=BROWSERBASE_API_KEY)
        self.clinics = self._load_clinics()
    
    def _load_clinics(self) -> Dict[str, Any]:
        """Load clinics from the input JSON file."""
        try:
            with open(INPUT_JSON, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"Error loading clinics from {INPUT_JSON}: {e}")
            return {}
    
    def _save_results(self, results: Dict[str, Any]) -> None:
        """Save the results to the output JSON file."""
        try:
            with open(OUTPUT_JSON, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to {OUTPUT_JSON}")
        except Exception as e:
            logger.error(f"Error saving results to {OUTPUT_JSON}: {e}")
    
    def create_agent_for_clinic(self, clinic: Dict[str, Any]) -> Agent:
        """Create a CrewAI agent for a single clinic using Claude."""
        clinic_name = clinic.get('name', 'Unknown Clinic')
        
        # Initialize OpenAI GPT-4
        llm = ChatOpenAI(
            model="gpt-4-turbo-preview",  # Using GPT-4 Turbo
            temperature=0.1,
            max_tokens=4000
        )
        
        # Create agent with minimal required parameters
        return Agent(
            role=f"Appointment Finder for {clinic_name}",
            goal=f"Find available appointment times at {clinic_name} by visiting their website",
            backstory=f"""You are an AI assistant specialized in finding available appointment times at medical clinics. 
            You carefully navigate clinic websites to locate and extract appointment availability information.
            Be thorough and check all relevant sections of the website.""",
            llm=llm,
            tools=[self.create_browserbase_tool()],
            allow_delegation=False,
            max_iterations=3
        )
    
    def _create_browserbase_session(self):
        """Helper method to create a new BrowserBase session with retry logic."""
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                session = self.browserbase_client.sessions.create(
                    project_id=BROWSERBASE_PROJECT_ID
                )
                return session
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Session creation attempt {attempt + 1} failed: {e}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
        return None
    
    def _close_browserbase_session(self, session):
        """Helper method to safely close a BrowserBase session."""
        if not session:
            return
            
        try:
            if hasattr(session, 'close'):
                session.close()
            # Add any additional cleanup needed
        except Exception as e:
            logger.warning(f"Error closing BrowserBase session: {e}")
    
    def create_browserbase_tool(self):
        """Create a tool that uses BrowserBase to visit websites."""
        from crewai.tools.agent_tools import Tool
        from pydantic import BaseModel, Field
        
        # Define the input schema using Pydantic BaseModel
        class BrowserWebsiteInput(BaseModel):
            url: str = Field(..., description="The URL of the website to visit")
        
        def browse_website(url: str) -> str:
            """
            Visit a website and return its content.
            
            Args:
                url: The URL of the website to visit
                
            Returns:
                str: A JSON string containing the page content, screenshot URL, and found keywords
            """
            session = None
            try:
                logger.info(f"Creating BrowserBase session for {url}")
                session = self._create_browserbase_session()
                if not session:
                    raise Exception("Failed to create BrowserBase session after multiple attempts")
                
                # Add a small delay before navigation
                time.sleep(2)
                
                # Navigate to the URL with timeout
                session.goto(url, timeout=30000)  # 30 second timeout
                
                # Wait for page to load
                time.sleep(3)
                
                # Take a screenshot for debugging
                screenshot_url = session.screenshot()
                logger.info(f"Screenshot available at: {screenshot_url}")
                
                # Get the page content with error handling
                try:
                    content = session.evaluate("document.body.innerText")
                except Exception as e:
                    content = f"Could not extract page content: {str(e)}"
                
                # Look for appointment-related content
                appointment_keywords = [
                    'appointment', 'book now', 'schedule', 'availability',
                    'book online', 'reserve', 'calendar', 'time slot',
                    'make an appointment', 'schedule appointment'
                ]
                
                found_keywords = [
                    kw for kw in appointment_keywords 
                    if kw.lower() in content.lower()
                ]
                
                result = {
                    'content': content[:1000] + '...' if len(content) > 1000 else content,
                    'screenshot': screenshot_url,
                    'found_keywords': found_keywords,
                    'timestamp': datetime.now().isoformat()
                }
                
                return json.dumps(result, indent=2)
                
            except Exception as e:
                error_msg = f"Error browsing {url}: {str(e)}"
                logger.error(error_msg)
                return json.dumps({
                    'error': error_msg,
                    'timestamp': datetime.now().isoformat()
                }, indent=2)
                
            finally:
                # Ensure session is always closed
                self._close_browserbase_session(session)
        
        # Create and return the tool with the proper schema
        return Tool(
            name="browse_website",
            func=browse_website,
            description="A tool to visit a website and extract content. The input should be a URL.",
            args_schema=BrowserWebsiteInput,
            return_direct=True
        )
    
    def create_task_for_clinic(self, clinic: Dict[str, Any]) -> Task:
        """Create a task for a clinic agent to find appointment availability."""
        website = clinic.get('website', '')
        clinic_name = clinic.get('name', 'the clinic')
        
        return Task(
            description=f"""
            Visit {website} and find available appointment times.
            
            Your task is to:
            1. Navigate to the clinic's website: {website}
            2. Look for any sections related to booking appointments
            3. If there's an online booking system, note how to access it
            4. If there are specific instructions for booking, summarize them
            5. If phone booking is required, note the phone number and hours
            6. Report any available appointment times you can find
            
            Be thorough and check multiple sections of the site if needed.
            """,
            agent=self.create_agent_for_clinic(clinic),
            expected_output=f"""
            A detailed report on appointment availability at {clinic_name} including:
            - Online booking availability (yes/no)
            - Steps to book an appointment
            - Available time slots (if shown)
            - Phone number for booking (if required)
            - Any other relevant information
            """
        )
    
    def process_clinics(self) -> Dict[str, Any]:
        """Process all clinics sequentially and return the results."""
        results = {}
        
        # Process each location in the input JSON
        for location, clinics in self.clinics.items():
            if location == 'metadata':
                results[location] = clinics
                continue
                
            results[location] = []
            
            for clinic in clinics:
                try:
                    clinic_name = clinic.get('name', 'Unknown Clinic')
                    logger.info(f"Processing clinic: {clinic_name}")
                    
                    # Create a crew with a single agent for this clinic
                    crew = Crew(
                        agents=[self.create_agent_for_clinic(clinic)],
                        tasks=[self.create_task_for_clinic(clinic)],
                        verbose=True,
                        process=Process.sequential
                    )
                    
                    # Run the crew for this clinic
                    result = crew.kickoff()
                    
                    # Add the result to our output
                    clinic_result = clinic.copy()
                    clinic_result['scraping_result'] = {
                        'status': 'success',
                        'timestamp': datetime.now().isoformat(),
                        'result': result
                    }
                    results[location].append(clinic_result)
                    
                    # Save after each clinic in case of failures
                    self._save_results(results)
                    
                    # Add a small delay between clinic processing
                    time.sleep(5)
                    
                except Exception as e:
                    logger.error(f"Error processing clinic {clinic.get('name')}: {e}")
                    clinic_result = clinic.copy()
                    clinic_result['scraping_result'] = {
                        'status': 'error',
                        'timestamp': datetime.now().isoformat(),
                        'error': str(e)
                    }
                    results[location].append(clinic_result)
                    
                    # Save error results and add a longer delay on error
                    self._save_results(results)
                    time.sleep(10)  # Longer delay on error
        
        return results

def main():
    """Main function to run the clinic scraper."""
    try:
        logger.info("Starting clinic scraper...")
        scraper = ClinicScraper()
        results = scraper.process_clinics()
        scraper._save_results(results)
        logger.info("Clinic scraping completed successfully!")
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)

if __name__ == "__main__":
    main()
