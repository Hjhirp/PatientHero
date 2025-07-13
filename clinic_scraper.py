import json
import asyncio
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Import Crew AI
from crewai import Agent, Task, Crew, Process
from crewai.agents.tools import BaseTool

# Import BrowserBase
from browserbase import Browserbase
from browserbase.helpers.gotopage import goto_page
from browserbase.helpers.screenshot import take_screenshot

# Import W&B for tracking
WANDB_AVAILABLE = False

def wandb_op(func):
    """Decorator that works whether W&B is available or not"""
    if not WANDB_AVAILABLE:
        return func
    
    try:
        import wandb
        return wandb.op()(func)
    except Exception as e:
        print(f"Warning: Failed to apply W&B decorator: {e}")
        return func

try:
    import wandb
    WANDB_AVAILABLE = True
    
    # Initialize W&B
    try:
        wandb.init(project="clinic-appointment-scraper")
        print("Weights & Biases tracking enabled")
    except Exception as e:
        print(f"Warning: Failed to initialize W&B: {e}")
        WANDB_AVAILABLE = False
        
except ImportError:
    print("Warning: wandb not installed. Tracking will be disabled.")
    print("Install with: pip install wandb")

@dataclass
class ClinicInfo:
    name: str
    website: str
    address: Optional[str] = None
    phone: Optional[str] = None
    specialty: Optional[str] = None

@dataclass
class AppointmentResult:
    crew_agent_id: str
    clinic_name: str
    website: str
    available_times: List[str]
    booking_links: List[str]
    success: bool
    error_message: str = ""
    timestamp: str = ""

class BrowserBaseTool(BaseTool):
    """Custom tool for BrowserBase integration with Crew AI"""
    
    name: str = "browser_automation"
    description: str = "Automates web browsing to find appointment booking information"
    
    def __init__(self, browserbase_client, **kwargs):
        super().__init__()
        self.browserbase_client = browserbase_client
        
    def _run(self, clinic_name: str, clinic_url: str, agent_id: str) -> Dict[str, Any]:
        """
        Use BrowserBase to visit clinic website and find appointment booking info
        """
        try:
            # Create a new browser session
            session = self.browserbase_client.sessions.create()
            
            try:
                # Navigate to the clinic website
                goto_page(session.id, clinic_url)
                
                # Take initial screenshot for debugging
                screenshot_url = take_screenshot(session.id)
                
                # Search for appointment-related links and information
                appointment_info = self._find_appointment_info(session.id, clinic_url)
                
                return {
                    "success": True,
                    "clinic_name": clinic_name,
                    "website": clinic_url,
                    "agent_id": agent_id,
                    "appointment_info": appointment_info,
                    "screenshot_url": screenshot_url
                }
                
            finally:
                # Always clean up the session
                self.browserbase_client.sessions.delete(session.id)
                
        except Exception as e:
            return {
                "success": False,
                "clinic_name": clinic_name,
                "website": clinic_url,
                "agent_id": agent_id,
                "error": str(e),
                "appointment_info": {"available_times": [], "booking_links": []}
            }
    
    def _run(self, clinic_name: str, clinic_url: str, agent_id: str) -> Dict[str, Any]:
        """
        Use BrowserBase to visit clinic website and find appointment booking info
        """
        try:
            # Create a new browser session
            session = self.browserbase_client.sessions.create()
            
            try:
                # Navigate to the clinic website
                goto_page(session.id, clinic_url)
                
                # Take initial screenshot for debugging
                screenshot_url = take_screenshot(session.id)
                
                # Search for appointment-related links and information
                appointment_info = self._find_appointment_info(session.id, clinic_url)
                
                return {
                    "success": True,
                    "clinic_name": clinic_name,
                    "website": clinic_url,
                    "agent_id": agent_id,
                    "appointment_info": appointment_info,
                    "screenshot_url": screenshot_url
                }
                
            finally:
                # Always clean up the session
                self.browserbase_client.sessions.delete(session.id)
                
        except Exception as e:
            return {
                "success": False,
                "clinic_name": clinic_name,
                "website": clinic_url,
                "agent_id": agent_id,
                "error": str(e),
                "appointment_info": {"available_times": [], "booking_links": []}
            }
    
    def _find_appointment_info(self, session_id: str, base_url: str) -> Dict[str, List[str]]:
        """
        Navigate the website to find appointment booking information
        """
        # JavaScript to execute in the browser to find appointment-related elements
        appointment_search_script = """
        function findAppointmentInfo() {
            const results = {
                booking_links: [],
                available_times: [],
                appointment_text: []
            };
            
            // Search for appointment-related links
            const appointmentKeywords = [
                'appointment', 'booking', 'schedule', 'book now', 
                'reserve', 'calendar', 'availability', 'book online',
                'patient portal', 'schedule online', 'make an appointment'
            ];
            
            // Find all links
            const links = document.querySelectorAll('a[href]');
            links.forEach(link => {
                const text = link.textContent.toLowerCase();
                const href = link.href;
                
                for (const keyword of appointmentKeywords) {
                    if (text.includes(keyword) || href.includes(keyword)) {
                        results.booking_links.push({
                            text: link.textContent.trim(),
                            href: href,
                            keyword_matched: keyword
                        });
                        break;
                    }
                }
            });
            
            // Search for time-related text (available appointment times)
            const timePatterns = [
                /\b\d{1,2}:\d{2}\s*(AM|PM|am|pm)\b/g,
                /\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday).*\d{1,2}:\d{2}/gi,
                /\b\d{1,2}\/\d{1,2}\/\d{2,4}\b/g,
                /\bavailable.*\d{1,2}:\d{2}/gi
            ];
            
            const bodyText = document.body.textContent;
            timePatterns.forEach(pattern => {
                const matches = bodyText.match(pattern);
                if (matches) {
                    results.available_times.push(...matches);
                }
            });
            
            // Look for common appointment scheduling widgets/iframes
            const iframes = document.querySelectorAll('iframe');
            iframes.forEach(iframe => {
                const src = iframe.src ? iframe.src.toLowerCase() : '';
                if (src.includes('calendar') || src.includes('booking') || 
                    src.includes('schedule') || src.includes('appointment')) {
                    results.booking_links.push({
                        text: 'Embedded booking widget',
                        href: iframe.src,
                        keyword_matched: 'embedded_widget'
                    });
                }
            });
            
            return results;
        }
        
        return findAppointmentInfo();
        """
        
        try:
            result = self.browserbase_client.sessions.execute_script(
                session_id, 
                appointment_search_script
            )
            
            # Process and clean the results
            booking_links = []
            available_times = set()  # Use set to avoid duplicates
            
            if result and 'booking_links' in result:
                for link_info in result['booking_links']:
                    if link_info.get('href'):
                        booking_links.append(link_info['href'])
            
            if result and 'available_times' in result:
                for time_str in result['available_times']:
                    if time_str and time_str.strip():
                        available_times.add(time_str.strip())
            
            return {
                "booking_links": list(booking_links),
                "available_times": list(available_times)
            }
            
        except Exception as e:
            print(f"Error executing appointment search script: {e}")
            return {"booking_links": [], "available_times": []}

class ClinicScrapingAgent:
    """Individual agent responsible for scraping one clinic website"""
    
    def __init__(self, clinic_info: ClinicInfo, browserbase_client, agent_id: str):
        self.clinic_info = clinic_info
        self.agent_id = agent_id
        self.browserbase_tool = BrowserBaseTool(browserbase_client)
        
        # Create Crew AI agent
        self.agent = Agent(
            role='Clinic Website Scraper',
            goal=f'Find appointment booking information for {clinic_info.name}',
            backstory=f"""You are an expert web scraper specialized in finding 
            appointment booking information on medical clinic websites. You are 
            assigned to analyze {clinic_info.name} at {clinic_info.website}""",
            verbose=True,
            allow_delegation=False,
            tools=[self.browserbase_tool]
        )
        
        # Create task for this agent
        self.task = Task(
            description=f"""
            Visit the clinic website at {clinic_info.website} and find:
            1. Any links related to booking appointments
            2. Available appointment times if visible
            3. Online booking systems or patient portals
            
            Return structured information about appointment availability.
            """,
            agent=self.agent,
            expected_output="Structured data about appointment booking options and available times"
        )
    
    def scrape_clinic(self) -> AppointmentResult:
        """Execute the scraping task for this clinic"""
        try:
            # Execute the browser automation tool
            result = self.browserbase_tool._run(
                clinic_name=self.clinic_info.name,
                clinic_url=self.clinic_info.website,
                agent_id=self.agent_id
            )
            
            if result["success"]:
                appointment_info = result["appointment_info"]
                return AppointmentResult(
                    crew_agent_id=self.agent_id,
                    clinic_name=self.clinic_info.name,
                    website=self.clinic_info.website,
                    available_times=appointment_info.get("available_times", []),
                    booking_links=appointment_info.get("booking_links", []),
                    success=True,
                    timestamp=datetime.now().isoformat()
                )
            else:
                return AppointmentResult(
                    crew_agent_id=self.agent_id,
                    clinic_name=self.clinic_info.name,
                    website=self.clinic_info.website,
                    available_times=[],
                    booking_links=[],
                    success=False,
                    error_message=result.get("error", "Unknown error"),
                    timestamp=datetime.now().isoformat()
                )
                
        except Exception as e:
            return AppointmentResult(
                crew_agent_id=self.agent_id,
                clinic_name=self.clinic_info.name,
                website=self.clinic_info.website,
                available_times=[],
                booking_links=[],
                success=False,
                error_message=str(e),
                timestamp=datetime.now().isoformat()
            )

class ClinicAppointmentOrchestrator:
    """Main orchestrator that manages all clinic scraping agents"""
    
    def __init__(self, browserbase_api_key: str):
        self.browserbase_client = Browserbase(api_key=browserbase_api_key)
        self.agents: List[ClinicScrapingAgent] = []
        self.results: List[AppointmentResult] = []
    
    def load_clinics_from_json(self, json_file_path: str) -> List[ClinicInfo]:
        """Load clinic information from JSON file"""
        try:
            with open(json_file_path, 'r') as file:
                data = json.load(file)
            
            clinics = []
            # Extract all clinic groups (like 'clinics_houston_77065')
            for clinic_group in data:
                if clinic_group != 'metadata' and isinstance(data[clinic_group], list):
                    for clinic_data in data[clinic_group]:
                        if 'name' in clinic_data and 'website' in clinic_data:
                            clinics.append(ClinicInfo(
                                name=clinic_data['name'],
                                website=clinic_data['website'],
                                address=clinic_data.get('address'),
                                phone=clinic_data.get('phone'),
                                specialty=clinic_data.get('specialty')
                            ))
            
            return clinics
            
        except Exception as e:
            print(f"Error loading clinics from JSON: {e}")
            return []
    
    def create_agents(self, clinics: List[ClinicInfo]) -> None:
        """Create a Crew AI agent for each clinic"""
        self.agents = []
        
        for i, clinic in enumerate(clinics):
            agent_id = f"clinic_agent_{i}_{clinic.name.replace(' ', '_').lower()[:20]}"
            
            scraping_agent = ClinicScrapingAgent(
                clinic_info=clinic,
                browserbase_client=self.browserbase_client,
                agent_id=agent_id
            )
            
            self.agents.append(scraping_agent)
            print(f"Created agent {agent_id} for {clinic.name}")
    
    async def scrape_all_clinics_parallel(self, max_workers: int = 3) -> List[AppointmentResult]:
        """Execute all clinic scraping tasks in parallel"""
        results = []
        
        # Use ThreadPoolExecutor for parallel execution
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all scraping tasks
            future_to_agent = {
                executor.submit(agent.scrape_clinic): agent 
                for agent in self.agents
            }
            
            # Collect results as they complete
            for future in future_to_agent:
                try:
                    result = future.result(timeout=120)  # 120 second timeout per clinic
                    results.append(result)
                    
                    if result.success and (result.available_times or result.booking_links):
                        print(f"✅ Found appointments for {result.clinic_name}")
                        if result.available_times:
                            print(f"   Available times: {result.available_times}")
                        if result.booking_links:
                            print(f"   Booking links: {result.booking_links}")
                    else:
                        error_msg = f" - {result.error_message}" if result.error_message else ""
                        print(f"❌ No appointments found for {result.clinic_name}{error_msg}")
                            
                except Exception as e:
                    agent = future_to_agent[future]
                    print(f"❌ Error scraping {agent.clinic_info.name}: {e}")
                    results.append(AppointmentResult(
                        crew_agent_id=agent.agent_id,
                        clinic_name=agent.clinic_info.name,
                        website=agent.clinic_info.website,
                        available_times=[],
                        booking_links=[],
                        success=False,
                        error_message=str(e),
                        timestamp=datetime.now().isoformat()
                    ))
        
        self.results = results
        return results
    
    def get_successful_results(self) -> List[AppointmentResult]:
        """Get only the results that found appointment information"""
        return [
            result for result in self.results 
            if result.success and (result.available_times or result.booking_links)
        ]
    
    def save_results_to_json(self, input_file: str, output_file: str = "test_clinic_list_with_appts.json") -> None:
        """Save all results to a new JSON file that includes the original data plus appointment info"""
        try:
            # Load the original data
            with open(input_file, 'r') as file:
                data = json.load(file)
            
            # Create a mapping of clinic names to appointment results
            results_by_clinic = {
                result.clinic_name: {
                    "available_times": result.available_times,
                    "booking_links": result.booking_links,
                    "success": result.success,
                    "error_message": result.error_message,
                    "last_checked": result.timestamp
                }
                for result in self.results
            }
            
            # Add appointment info to each clinic in the original data
            for clinic_group in data:
                if clinic_group != 'metadata' and isinstance(data[clinic_group], list):
                    for clinic in data[clinic_group]:
                        if 'name' in clinic and clinic['name'] in results_by_clinic:
                            clinic["appointment_info"] = results_by_clinic[clinic['name']]
            
            # Add metadata about when the scraping was performed
            if "metadata" not in data:
                data["metadata"] = {}
            
            data["metadata"]["last_scraped"] = datetime.now().isoformat()
            data["metadata"]["total_clinics_processed"] = len(self.results)
            data["metadata"]["successful_scrapes"] = sum(1 for r in self.results if r.success)
            
            # Save the enhanced data to the output file
            with open(output_file, 'w') as file:
                json.dump(data, file, indent=2)
            
            print(f"Results saved to {output_file}")
            
        except Exception as e:
            print(f"Error saving results to JSON: {e}")
            
            # Fallback: Save just the results if we can't merge with the input
            try:
                results_data = [asdict(result) for result in self.results]
                with open("appointment_results_fallback.json", 'w') as file:
                    json.dump({"results": results_data}, file, indent=2)
                print("Saved raw results to appointment_results_fallback.json")
            except Exception as e2:
                print(f"Failed to save fallback results: {e2}")

# Main execution function
@wandb_op
async def main():
    """Main function to orchestrate clinic appointment scraping"""
    
    # Configuration
    BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY")
    if not BROWSERBASE_API_KEY:
        print("Error: BROWSERBASE_API_KEY environment variable not set")
        print("Please set your BrowserBase API key and try again.")
        print("You can get an API key at https://browserbase.com/")
        return
    
    INPUT_FILE = "test_clinic_list.json"
    OUTPUT_FILE = "test_clinic_list_with_appts.json"
    MAX_WORKERS = 2  # Reduced to avoid rate limiting
    
    # Initialize orchestrator
    print("Initializing Clinic Appointment Scraper...")
    orchestrator = ClinicAppointmentOrchestrator(BROWSERBASE_API_KEY)
    
    # Load clinic data
    print(f"\nLoading clinic data from {INPUT_FILE}...")
    clinics = orchestrator.load_clinics_from_json(INPUT_FILE)
    print(f"Loaded {len(clinics)} clinics")
    
    if not clinics:
        print("No valid clinic data found. Please check your JSON file.")
        return
    
    # Create agents
    print("\nCreating Crew AI agents...")
    orchestrator.create_agents(clinics)
    
    # Execute scraping
    print(f"\nStarting parallel clinic scraping with {MAX_WORKERS} workers...")
    print("This may take a few minutes. Please wait...\n")
    
    try:
        results = await orchestrator.scrape_all_clinics_parallel(max_workers=MAX_WORKERS)
        
        # Process results
        successful_results = orchestrator.get_successful_results()
        
        print(f"\n📊 SCRAPING COMPLETE:")
        print(f"   Total clinics processed: {len(results)}")
        print(f"   Successful appointments found: {len(successful_results)}")
        print(f"   Failed/No appointments: {len(results) - len(successful_results)}")
        
        # Display successful results
        if successful_results:
            print(f"\n🎯 CLINICS WITH AVAILABLE APPOINTMENTS:")
            for result in successful_results:
                print(f"\n   Clinic: {result.clinic_name}")
                if result.available_times:
                    print(f"   Available Times: {result.available_times}")
                if result.booking_links:
                    print(f"   Booking Links: {result.booking_links}")
        
        # Save results
        print(f"\n💾 Saving results to {OUTPUT_FILE}...")
        orchestrator.save_results_to_json(INPUT_FILE, OUTPUT_FILE)
        
        return successful_results
        
    except KeyboardInterrupt:
        print("\n⚠️  Scraping interrupted by user. Saving partial results...")
        orchestrator.save_results_to_json(INPUT_FILE, OUTPUT_FILE)
    except Exception as e:
        print(f"\n❌ An error occurred during scraping: {e}")
        print("Attempting to save any partial results...")
        orchestrator.save_results_to_json(INPUT_FILE, OUTPUT_FILE)
        raise

# Example usage and setup
if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())
