import os
import json
import uuid
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

import wandb

wandb.login()

import weave
import google.generativeai as genai
import requests
from crewai import Agent, Task, Crew, Process, BaseLLM
from crewai.llm import LLM

# Import the ExaHelper
from exa_helper import ExaHelper

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Set the Weave team and project for tracing
weave.init(os.getenv("WANDB_ENTITY", "mugiwara_luffy") + "/" + os.getenv("WANDB_PROJECT", "patienthero-crewai"))

@dataclass
class PatientData:
    """Data structure to store patient information"""
    session_id: str
    timestamp: str
    medical_condition: Optional[str] = None
    zip_code: Optional[str] = None
    phone_number: Optional[str] = None
    insurance: Optional[str] = None
    symptoms: Optional[List[str]] = None
    reasoning_analysis: Optional[str] = None
    conversation_history: List[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []
    
    def is_basic_info_complete(self) -> bool:
        """Check if all basic patient information is collected"""
        return all([
            self.medical_condition,
            self.zip_code,
            self.phone_number,
            self.insurance
        ])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

class WandbWeaveMonitor:
    """Monitor for tracking agent communications with Wandb Weave"""
    
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        
    @weave.op()
    def log_agent_interaction(self, agent_name: str, input_data: str, output_data: str, metadata: Dict = None):
        """Log agent interactions"""
        interaction_data = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "agent_name": agent_name,
            "input": input_data,
            "output": output_data,
            "metadata": metadata or {}
        }
        
        # Log to Wandb
        wandb.log({
            f"{agent_name}_interaction": interaction_data,
            "timestamp": datetime.now().timestamp()
        })
        
        return interaction_data
    
    @weave.op()
    def log_crew_execution(self, crew_result: str, patient_data: PatientData):
        """Log complete crew execution"""
        execution_data = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "crew_result": crew_result,
            "patient_data": patient_data.to_dict(),
            "completion_status": patient_data.is_basic_info_complete()
        }
        
        wandb.log({
            "crew_execution": execution_data,
            "patient_data_complete": patient_data.is_basic_info_complete()
        })
        
        return execution_data

class PatientHeroCrewAI:
    """Main class for managing CrewAI agents with Wandb Weave monitoring"""
    
    def __init__(self):
        self.monitor = WandbWeaveMonitor()
        self.patient_data = PatientData(
            session_id=self.monitor.session_id,
            timestamp=datetime.now().isoformat()
        )
        
        # Initialize ExaHelper for direct processing
        self.exa_helper = ExaHelper()
        
        # Initialize Wandb run
        wandb.init(
            project=os.getenv("WANDB_PROJECT", "patienthero-crewai"),
            entity=os.getenv("WANDB_ENTITY"),
            config={
                "model": "gemini-2.5-flash",
                "session_id": self.monitor.session_id,
                "inference_provider": "google-gemini"
            }
        )
        
        # Initialize custom Gemini LLM for CrewAI
        self.llm = GeminiLLM(
            model="gemini-2.5-flash",
            api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.7
        )
        
        self._create_agents()
        self._create_tasks()
        self._create_crew()

    def _pass_to_exa_helper(self):
        """Pass medical data directly to ExaHelper for processing"""
        try:
            medical_data = {
                "medical_condition": self.patient_data.medical_condition,
                "zip_code": self.patient_data.zip_code,
                "insurance": self.patient_data.insurance,
                "phone_suffix": ''.join(filter(str.isdigit, self.patient_data.phone_number or ""))[-4:] if self.patient_data.phone_number else "0000",
                "session_id": self.patient_data.session_id,
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"📤 Passing medical data directly to ExaHelper...")
            print(f"🏥 Condition: {medical_data['medical_condition']}")
            print(f"📍 Location: {medical_data['zip_code']}")
            print(f"🏢 Insurance: {medical_data['insurance']}")
            print()
            
            # Process patient data directly through ExaHelper
            processed_result = self.exa_helper.process_patient_from_main(medical_data)
            
            # Optional: Store the processed result for further use
            self.processed_patient_data = processed_result
            
            # Automatically trigger appointment processing after hospital search
            print(f"🔄 Triggering appointment processing for found hospitals...")
            try:
                import sys
                import os
                
                # Add current directory to path for import
                current_dir = os.path.dirname(os.path.dirname(__file__))
                if current_dir not in sys.path:
                    sys.path.append(current_dir)
                
                # Import and run appointment processing
                from process_clinics_parallel import process_medical_institutions_for_api
                
                # Use asyncio.create_task instead of run_until_complete to avoid loop conflict
                try:
                    # Try to get existing loop
                    current_loop = asyncio.get_running_loop()
                    # Schedule the appointment processing as a background task
                    task = current_loop.create_task(process_medical_institutions_for_api())
                    print(f"📅 Appointment processing started in background...")
                    # Store the task for later retrieval
                    self.appointment_task = task
                except RuntimeError:
                    # No loop running, create new one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    appointment_results = loop.run_until_complete(process_medical_institutions_for_api())
                    
                    if appointment_results:
                        print(f"✅ Successfully processed {len(appointment_results)} hospitals with appointment data")
                        # Store appointment results for later use
                        self.appointment_results = appointment_results
                        
                        # Save appointment results to a separate file for frontend access
                        with open('processed_medical_data_with_appointments.json', 'w') as f:
                            json.dump(appointment_results, f, indent=2)
                        print(f"💾 Appointment data saved to processed_medical_data_with_appointments.json")
                    else:
                        print(f"⚠️ No appointment data found during processing")
                        
            except Exception as appointment_error:
                print(f"⚠️ Error during appointment processing: {appointment_error}")
                # Continue with normal flow even if appointment processing fails
            
            return processed_result
            
        except Exception as e:
            print(f"⚠️ Error processing data with ExaHelper: {e}")
            return None
    
    def _create_agents(self):
        """Create the three CrewAI agents"""
        
        # Agent 1: Chat Inference Model for basic patient information
        self.chat_agent = Agent(
            role="Patient Information Collector",
            goal="Have a natural conversation with patients to gradually collect essential information including medical condition, zip code, phone number, and insurance details",
            backstory="""You are a friendly and professional medical intake specialist having a real conversation with a patient. 
            Your job is to gather basic patient information one piece at a time through natural dialogue. 
            You should be empathetic, patient, and conversational. Ask for one piece of missing information at a time.
            When a patient greets you, greet them back warmly and ask about what brings them in today.
            Never generate fake conversations or made-up data - only respond to what the patient actually says.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        # Agent 2: Reasoning Model for symptom analysis
        self.reasoning_agent = Agent(
            role="Medical Reasoning Specialist",
            goal="Analyze patient's medical condition and dive deeper into possible symptoms and related health concerns",
            backstory="""You are an experienced medical AI assistant specializing in 
            symptom analysis and medical reasoning. Based on the patient's reported condition, 
            you identify potential symptoms, ask relevant follow-up questions, and provide 
            preliminary analysis. You are thorough, evidence-based, and always remind patients 
            to consult with healthcare professionals.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        # Agent 3: Data Extraction Specialist
        self.extraction_agent = Agent(
            role="Data Extraction Specialist",
            goal="Extract and structure patient information from conversation data into standardized JSON format",
            backstory="""You are an expert data extraction specialist with deep knowledge 
            of medical terminology and patient information processing. Your role is to analyze 
            conversation transcripts and extract all relevant patient data, organizing it into 
            structured JSON format. You can identify medical conditions, personal information, 
            symptoms, and other relevant data from natural language conversations. You ensure 
            data accuracy and completeness while maintaining patient privacy standards.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    def _create_tasks(self):
        """Create tasks for each agent"""
        
        self.chat_task = Task(
            description="""You are having a conversation with a patient. Respond naturally to their input.
            
            Your goal is to gradually collect the following information through natural conversation:
            1. Medical condition they are experiencing
            2. ZIP code for location-based services  
            3. Phone number for contact
            4. Insurance information
            
            Based on the current patient data, determine what information is still needed and ask for ONE piece of missing information at a time. Be conversational, empathetic, and patient.
            
            If the user just says "Hi" or greets you, greet them back warmly and ask about their medical condition.
            If they provide information, acknowledge it and ask for the next missing piece.
            
            Current user input: {user_input}
            Current patient data: {current_data}
            
            Respond with a natural, conversational message - NOT a JSON object or structured data.
            """,
            agent=self.chat_agent,
            expected_output="A natural conversational response to the patient"
        )
        
        self.reasoning_task = Task(
            description="""You are now analyzing symptoms for a patient whose basic information has been collected.
            
            Based on the patient's reported medical condition and any new symptoms they mention, perform analysis:
            1. Identify potential symptoms associated with the condition
            2. Ask relevant follow-up questions about symptoms they've mentioned
            3. Provide preliminary medical reasoning (while emphasizing need for professional consultation)
            4. Suggest what additional information might be helpful
            
            If this is the initial reasoning analysis (user_input contains "Let's analyze your condition"), provide a comprehensive initial assessment and ask specific questions about their symptoms.
            If the patient mentions new symptoms, acknowledge them and dive deeper into those specific symptoms.
            Be conversational and empathetic while gathering more detailed symptom information.
            
            Patient's medical condition: {medical_condition}
            Current user input: {user_input}
            Current patient data: {current_data}
            
            Respond with a natural, conversational message focusing on symptom analysis.
            """,
            agent=self.reasoning_agent,
            expected_output="Detailed symptom analysis, follow-up questions, and medical reasoning in conversational format"
        )
        
        self.extraction_task = Task(
            description="""Extract and structure all patient information from the conversation data:
            
            Analyze the complete conversation history and extract:
            1. Personal Information:
               - Name (if mentioned)
               - Age (if mentioned)
               - Phone number
               - Address/ZIP code
               - Insurance information
            
            2. Medical Information:
               - Primary medical condition/complaint
               - Symptoms mentioned
               - Severity indicators
               - Duration of symptoms
               - Previous treatments mentioned
               - Medications mentioned
               - Allergies mentioned
            
            3. Additional Context:
               - Emergency contact information
               - Preferred language
               - Accessibility needs
               - Any other relevant information
            
            Output the extracted data in the following JSON format:
            {{
                "personal_info": {{
                    "name": "string or null",
                    "age": "string or null",
                    "phone": "string or null",
                    "zip_code": "string or null",
                    "address": "string or null",
                    "insurance": "string or null",
                    "emergency_contact": "string or null"
                }},
                "medical_info": {{
                    "primary_condition": "string or null",
                    "symptoms": ["array of symptoms"],
                    "severity": "string or null",
                    "duration": "string or null",
                    "previous_treatments": ["array of treatments"],
                    "current_medications": ["array of medications"],
                    "allergies": ["array of allergies"]
                }},
                "additional_context": {{
                    "preferred_language": "string or null",
                    "accessibility_needs": "string or null",
                    "notes": "string or null"
                }},
                "extraction_confidence": {{
                    "personal_info_confidence": "high/medium/low",
                    "medical_info_confidence": "high/medium/low",
                    "overall_completeness": "percentage"
                }}
            }}
            
            Conversation history: {conversation_history}
            Current extracted data: {current_data}
            """,
            agent=self.extraction_agent,
            expected_output="Complete structured JSON data with all extracted patient information and confidence scores"
        )
    
    def _create_crew(self):
        """Create separate crews for different phases"""
        # Chat crew for basic information collection
        self.chat_crew = Crew(
            agents=[self.chat_agent],
            tasks=[self.chat_task],
            process=Process.sequential,
            verbose=True
        )
        
        # Reasoning crew for symptom analysis
        self.reasoning_crew = Crew(
            agents=[self.reasoning_agent],
            tasks=[self.reasoning_task],
            process=Process.sequential,
            verbose=True
        )
        
        # Extraction crew for data structuring
        self.extraction_crew = Crew(
            agents=[self.extraction_agent],
            tasks=[self.extraction_task],
            process=Process.sequential,
            verbose=True
        )
    
    @weave.op()
    def process_user_input(self, user_input: str) -> Dict[str, Any]:
        """Process user input through the appropriate workflow"""
        
        # Add user input to conversation history
        self.patient_data.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "speaker": "user",
            "message": user_input
        })
        
        # Log user input
        self.monitor.log_agent_interaction(
            "user_input", 
            "", 
            user_input, 
            {"step": "user_input"}
        )
        
        if not self.patient_data.is_basic_info_complete():
            # Use chat agent to collect basic information
            response = self._collect_basic_info(user_input)
            return response
        else:
            # Use reasoning agent for symptom analysis
            response = self._analyze_symptoms(user_input)
            
            # Run extraction agent after reasoning to update structured data
            try:
                extraction_result = self._extract_structured_data()
                response["extraction_data"] = extraction_result
            except Exception as e:
                print(f"⚠️ Error running extraction after reasoning: {e}")
            
            return response
    
    def _collect_basic_info(self, user_input: str) -> Dict[str, Any]:
        """Collect basic patient information using chat agent"""
        
        # Prepare context for the chat agent
        crew_input = {
            "user_input": user_input,
            "current_data": self.patient_data.to_dict()
        }
        
        # Execute chat task only
        result = self.chat_crew.kickoff(inputs=crew_input)
        
        # Log chat agent interaction
        self.monitor.log_agent_interaction(
            "chat_agent",
            user_input,
            str(result),
            {"step": "basic_info_collection", "data_complete": self.patient_data.is_basic_info_complete()}
        )
        
        # Extract and update patient data from user input using extraction agent
        self._extract_and_update_patient_data(user_input)
        
        # Add agent response to conversation history
        self.patient_data.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "speaker": "chat_agent",
            "message": str(result)
        })
        
        # Check if we now have complete basic info after this interaction
        basic_info_complete = self.patient_data.is_basic_info_complete()
        
        response = {
            "agent": "chat_agent",
            "response": str(result),
            "patient_data": self.patient_data.to_dict(),
            "next_step": "reasoning_analysis" if basic_info_complete else "continue_basic_info"
        }
        
        # Save data and notify if basic info is complete
        if basic_info_complete:
            self._save_patient_data()
            print(f"\n✅ Basic patient information collection complete!")
            print(f"📋 Collected: Medical condition, ZIP code, phone number, and insurance")
            print(f"🔄 Switching to Reasoning Agent for symptom analysis...")
            
            # Automatically provide a reasoning response to continue the flow
            reasoning_response = self._analyze_symptoms("Let's analyze your condition in more detail")
            
            # Update the response to include reasoning analysis
            response.update({
                "agent": "reasoning_agent",
                "response": f"{str(result)}\n\n{reasoning_response['response']}",
                "next_step": "continue_symptom_analysis",
                "transition": "basic_info_to_reasoning"
            })
            
            # Run extraction agent after basic info is complete
            try:
                extraction_result = self._extract_structured_data()
                response["extraction_data"] = extraction_result
            except Exception as e:
                print(f"⚠️ Error running extraction after basic info completion: {e}")
        
        return response
    
    def _analyze_symptoms(self, user_input: str) -> Dict[str, Any]:
        """Analyze symptoms using reasoning agent"""
        
        print(f"🧠 Reasoning Agent activated - analyzing symptoms for: {self.patient_data.medical_condition}")
        
        # Prepare context for reasoning agent
        crew_input = {
            "medical_condition": self.patient_data.medical_condition or "Not specified",
            "current_data": self.patient_data.to_dict(),
            "user_input": user_input
        }
        
        # Execute reasoning task only
        result = self.reasoning_crew.kickoff(inputs=crew_input)
        
        # Log reasoning agent interaction
        self.monitor.log_agent_interaction(
            "reasoning_agent",
            user_input,
            str(result),
            {"step": "symptom_analysis", "medical_condition": self.patient_data.medical_condition}
        )
        
        # Update reasoning analysis
        self.patient_data.reasoning_analysis = str(result)
        
        # Add to conversation history
        self.patient_data.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "speaker": "reasoning_agent",
            "message": str(result)
        })
        
        # Save updated data
        self._save_patient_data()
        
        # Log complete crew execution
        self.monitor.log_crew_execution(str(result), self.patient_data)
        
        response = {
            "agent": "reasoning_agent",
            "response": str(result),
            "patient_data": self.patient_data.to_dict(),
            "next_step": "continue_symptom_analysis"
        }
        
        return response
    
    @weave.op()
    def _extract_structured_data(self) -> Dict[str, Any]:
        """Extract structured data using the extraction agent"""
        
        # Prepare context for extraction agent
        extraction_input = {
            "conversation_history": self.patient_data.conversation_history,
            "current_data": self.patient_data.to_dict()
        }
        
        # Execute extraction task only
        result = self.extraction_crew.kickoff(inputs=extraction_input)
        
        # Log extraction agent interaction
        self.monitor.log_agent_interaction(
            "extraction_agent",
            json.dumps(extraction_input, indent=2),
            str(result),
            {"step": "data_extraction", "conversation_length": len(self.patient_data.conversation_history)}
        )
        
        # Try to parse the JSON result
        try:
            if isinstance(result, str):
                # Extract JSON from the result if it's embedded in text
                import re
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    structured_data = json.loads(json_match.group())
                else:
                    # If no JSON found, create a structured response
                    structured_data = {
                        "extraction_result": result,
                        "format": "text_only"
                    }
            else:
                structured_data = result
                
        except json.JSONDecodeError:
            # If JSON parsing fails, wrap the result
            structured_data = {
                "extraction_result": str(result),
                "format": "raw_text",
                "error": "Failed to parse JSON"
            }
        except Exception as e:
            structured_data = {
                "extraction_result": str(result),
                "format": "error",
                "error": str(e)
            }
        
        # Add extraction metadata
        structured_data["extraction_metadata"] = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.patient_data.session_id,
            "conversation_turns": len(self.patient_data.conversation_history)
        }
        
        # Save the extracted data
        self._save_extracted_data(structured_data)
        
        return structured_data
    
    def _save_extracted_data(self, extracted_data: Dict[str, Any]):
        """Save extracted structured data to a separate JSON file"""
        output_path = os.getenv("EXTRACTED_DATA_OUTPUT_PATH", "./extracted_patient_data.json")
        
        # Create extraction entry
        extraction_entry = {
            "session_id": self.patient_data.session_id,
            "timestamp": datetime.now().isoformat(),
            "extracted_data": extracted_data,
            "raw_conversation": self.patient_data.conversation_history
        }
        
        # Load existing extractions
        existing_extractions = []
        if os.path.exists(output_path):
            try:
                with open(output_path, 'r') as f:
                    existing_extractions = json.load(f)
            except json.JSONDecodeError:
                existing_extractions = []
        
        # Add current extraction
        existing_extractions.append(extraction_entry)
        
        # Save updated extractions
        with open(output_path, 'w') as f:
            json.dump(existing_extractions, f, indent=2)
        
        print(f"Extracted data saved to {output_path}")

    def _extract_and_update_patient_data(self, user_input: str):
        """Use extraction agent to intelligently parse and update patient data from user input"""
        
        # Create a focused extraction task for the current input
        extraction_task = Task(
            description=f"""Extract patient information from this specific user input: "{user_input}"
            
            Current patient data: {self.patient_data.to_dict()}
            
            Focus on extracting:
            1. Medical condition/complaint (symptoms, pain, illness, health issues)
            2. ZIP code (5-digit postal codes)
            3. Phone number (any format: XXX-XXX-XXXX, (XXX) XXX-XXXX, etc.)
            4. Insurance information (provider names, policy details)
            5. Any additional symptoms or medical details
            
            Return ONLY the new information found in this input, formatted as JSON:
            {{
                "medical_condition": "extracted condition or null",
                "zip_code": "extracted zip code or null", 
                "phone_number": "extracted phone number or null",
                "insurance": "extracted insurance info or null",
                "additional_symptoms": ["any symptoms mentioned"],
                "confidence": "high/medium/low"
            }}
            
            If no relevant information is found, return {{"found": false}}
            """,
            agent=self.extraction_agent,
            expected_output="JSON object with extracted patient data or {found: false}"
        )
        
        # Create temporary crew for this extraction
        temp_extraction_crew = Crew(
            agents=[self.extraction_agent],
            tasks=[extraction_task],
            process=Process.sequential,
            verbose=False  # Keep it quiet for inline extraction
        )
        
        try:
            # Execute extraction
            result = temp_extraction_crew.kickoff()
            
            # Parse the extraction result
            import re
            json_match = re.search(r'\{.*\}', str(result), re.DOTALL)
            if json_match:
                extracted_data = json.loads(json_match.group())
                
                # Update patient data with extracted information
                if extracted_data.get("found", True):  # Default to True if not specified
                    if extracted_data.get("medical_condition") and not self.patient_data.medical_condition:
                        self.patient_data.medical_condition = extracted_data["medical_condition"]
                        print(f"✅ Extracted medical condition: {extracted_data['medical_condition']}")
                    
                    if extracted_data.get("zip_code") and not self.patient_data.zip_code:
                        self.patient_data.zip_code = extracted_data["zip_code"]
                        print(f"✅ Extracted ZIP code: {extracted_data['zip_code']}")
                    
                    if extracted_data.get("phone_number") and not self.patient_data.phone_number:
                        self.patient_data.phone_number = extracted_data["phone_number"]
                        print(f"✅ Extracted phone number: {extracted_data['phone_number']}")
                    
                    if extracted_data.get("insurance") and not self.patient_data.insurance:
                        self.patient_data.insurance = extracted_data["insurance"]
                        print(f"✅ Extracted insurance: {extracted_data['insurance']}")
                    
                    # Handle additional symptoms
                    if extracted_data.get("additional_symptoms"):
                        if not self.patient_data.symptoms:
                            self.patient_data.symptoms = []
                        for symptom in extracted_data["additional_symptoms"]:
                            if symptom not in self.patient_data.symptoms:
                                self.patient_data.symptoms.append(symptom)
                                print(f"✅ Added symptom: {symptom}")
                    
                    # If we got symptoms but no medical condition, and this is the first interaction,
                    # use the first symptom as the medical condition
                    if (not self.patient_data.medical_condition and 
                        self.patient_data.symptoms and 
                        len(self.patient_data.conversation_history) <= 3):  # Early in conversation
                        self.patient_data.medical_condition = f"Patient reports: {', '.join(self.patient_data.symptoms)}"
                        print(f"✅ Using symptoms as medical condition: {self.patient_data.medical_condition}")
            
        except Exception as e:
            print(f"⚠️ Extraction failed, falling back to simple parsing: {e}")
            # Fallback to simple extraction if agent fails
            self._simple_data_extraction(user_input)
        
        # Check and display progress
        self._display_collection_progress()
    
    def _simple_data_extraction(self, user_input: str):
        """Fallback simple extraction method"""
        user_input_lower = user_input.lower()
        import re
        
        # Extract medical condition (more comprehensive keywords)
        if not self.patient_data.medical_condition:
            medical_keywords = ['pain', 'ache', 'hurt', 'sick', 'condition', 'problem', 'headache', 'fever', 'nausea', 'dizzy', 'cough', 'cold', 'flu', 'infection', 'injury', 'broken', 'sprain', 'cut', 'burn', 'rash', 'allergy']
            if any(word in user_input_lower for word in medical_keywords):
                self.patient_data.medical_condition = user_input.strip()
                print(f"📝 Medical condition captured: {self.patient_data.medical_condition}")
        
        # Extract ZIP code (5 digit pattern)
        if not self.patient_data.zip_code:
            zip_match = re.search(r'\b\d{5}\b', user_input)
            if zip_match:
                self.patient_data.zip_code = zip_match.group()
                print(f"📍 ZIP code captured: {self.patient_data.zip_code}")
        
        # Extract phone number (various formats)
        if not self.patient_data.phone_number:
            phone_patterns = [
                r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # 555-123-4567 or 555.123.4567 or 5551234567
                r'\(\d{3}\)\s*\d{3}[-.]?\d{4}',   # (555) 123-4567
                r'\b\d{10}\b'                      # 5551234567
            ]
            for pattern in phone_patterns:
                phone_match = re.search(pattern, user_input)
                if phone_match:
                    self.patient_data.phone_number = phone_match.group()
                    print(f"📞 Phone number captured: {self.patient_data.phone_number}")
                    break
        
        # Extract insurance (keywords and providers)
        if not self.patient_data.insurance:
            insurance_keywords = ['insurance', 'aetna', 'blue cross', 'bluecross', 'medicare', 'medicaid', 'cigna', 'humana', 'anthem', 'kaiser', 'bcbs', 'united healthcare', 'unitedhealthcare']
            if any(word in user_input_lower for word in insurance_keywords):
                self.patient_data.insurance = user_input.strip()
                print(f"🏥 Insurance captured: {self.patient_data.insurance}")
    
    def _display_collection_progress(self):
        """Display progress of information collection"""
        missing_info = []
        if not self.patient_data.medical_condition:
            missing_info.append("medical condition")
        if not self.patient_data.zip_code:
            missing_info.append("ZIP code")
        if not self.patient_data.phone_number:
            missing_info.append("phone number")
        if not self.patient_data.insurance:
            missing_info.append("insurance")
        
        if missing_info:
            print(f"⏳ Still need: {', '.join(missing_info)}")
        else:
            print(f"✅ All basic information collected!")
    
    def _save_patient_data(self):
        """Save patient data to JSON file with phone number suffix"""
        # Generate filename based on last 4 digits of phone number
        phone_suffix = "0000"  # Default suffix
        if self.patient_data.phone_number:
            # Extract last 4 digits from phone number
            phone_digits = ''.join(filter(str.isdigit, self.patient_data.phone_number))
            if len(phone_digits) >= 4:
                phone_suffix = phone_digits[-4:]
        
        output_path = f"./patient_data_{phone_suffix}.json"
        
        # Load existing data for this phone number
        existing_data = []
        if os.path.exists(output_path):
            try:
                with open(output_path, 'r') as f:
                    existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = []
        
        # Add current patient data
        existing_data.append(self.patient_data.to_dict())
        
        # Save updated data
        with open(output_path, 'w') as f:
            json.dump(existing_data, f, indent=2)
        
        print(f"Patient data saved to {output_path}")
        
        # Pass medical data to ExaHelper if basic info is complete
        if self.patient_data.is_basic_info_complete():
            self._pass_to_exa_helper()
            # --- New: Save ExaHelper result to JSON file ---
            try:
                exa_result = self.search_nearby_institutions(
                    self.patient_data.medical_condition,
                    self.patient_data.zip_code,
                    self.patient_data.insurance
                )
                exa_output_path = f"./institutions_{phone_suffix}.json"
                with open(exa_output_path, 'w') as f:
                    json.dump(exa_result, f, indent=2)
                print(f"Nearby institutions saved to {exa_output_path}")
            except Exception as e:
                print(f"⚠️ Error saving Exa institutions: {e}")
    
    def get_patient_status(self) -> Dict[str, Any]:
        """Get current patient data status"""
        return {
            "session_id": self.patient_data.session_id,
            "basic_info_complete": self.patient_data.is_basic_info_complete(),
            "patient_data": self.patient_data.to_dict(),
            "next_step": "reasoning_analysis" if self.patient_data.is_basic_info_complete() else "continue_basic_info"
        }
    
    @weave.op()
    def run_llm_chat(self, messages: List[Dict[str, str]], context: str = "") -> str:
        """Trace LLM calls with Weave using Google Gemini API"""
        try:
            # Initialize Gemini model
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Convert messages to Gemini format
            if messages and messages[0].get("role") == "system":
                # Use system message as context and combine with user message
                system_msg = messages[0]["content"]
                user_msgs = [msg["content"] for msg in messages[1:] if msg.get("role") == "user"]
                prompt = f"System: {system_msg}\n\nUser: {' '.join(user_msgs)}"
            else:
                # Just use user messages
                user_msgs = [msg["content"] for msg in messages if msg.get("role") == "user"]
                prompt = ' '.join(user_msgs)
            
            response = model.generate_content(prompt)
            
            # Check if response was blocked or empty
            if not response.text or response.text.strip() == "":
                return "I understand you're seeking medical assistance. I'm here to help guide you through this process. Please provide more details about your situation."
            
            return response.text
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error calling Gemini API: {e}")
            return f"Error: {str(e)}"

class GeminiLLM(BaseLLM):
    """Custom LLM class for Google Gemini API integration with CrewAI"""
    
    def __init__(self, model: str, api_key: str, temperature: Optional[float] = 0.7):
        # IMPORTANT: Call super().__init__() with required parameters
        super().__init__(model=model, temperature=temperature)
        
        self.api_key = api_key
        self.model_name = model
        genai.configure(api_key=api_key)
        
    def call(
        self,
        messages: Union[str, List[Dict[str, str]]],
        tools: Optional[List[dict]] = None,
        callbacks: Optional[List[Any]] = None,
        available_functions: Optional[Dict[str, Any]] = None,
        **kwargs  # Accept any additional keyword arguments that CrewAI might pass
    ) -> Union[str, Any]:
        """Call the Google Gemini API with the given messages."""
        try:
            # Initialize Gemini model
            model = genai.GenerativeModel(self.model_name)
            
            # Convert messages to prompt format
            if isinstance(messages, str):
                prompt = messages
            else:
                # Convert message list to prompt
                if messages and messages[0].get("role") == "system":
                    # Use system message as context and combine with user message
                    system_msg = messages[0]["content"]
                    user_msgs = [msg["content"] for msg in messages[1:] if msg.get("role") == "user"]
                    prompt = f"System: {system_msg}\n\nUser: {' '.join(user_msgs)}"
                else:
                    # Just use user messages
                    user_msgs = [msg["content"] for msg in messages if msg.get("role") == "user"]
                    prompt = ' '.join(user_msgs)
            
            # Generate content with Gemini
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=1500,
                ),
                safety_settings=[
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
            )
            
            # Check if response was blocked or empty
            if not response.text or response.text.strip() == "":
                return "I understand you're seeking medical guidance. Let me provide some general supportive information while you prepare for your healthcare visit. Please consult with medical professionals for specific advice about your condition."
            
            return response.text
            
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return f"Error: Unable to connect to Gemini API - {str(e)}"
        
    def supports_function_calling(self) -> bool:
        """Override if your LLM supports function calling."""
        return True  # Gemini supports function calling
        
    def get_context_window_size(self) -> int:
        """Return the context window size of the Gemini model."""
        return 32768  # Gemini-1.5-flash context window

# Example usage and testing
if __name__ == "__main__":
    # Initialize the system
    patient_hero = PatientHeroCrewAI()
    
    print("PatientHero CrewAI System with Google Gemini API")
    print("==============================================")
    print("🤖 Model: gemini-2.5-flash (via Google AI)")
    print("📊 Monitoring: Wandb Weave tracing enabled")
    print("")
    print("This system includes three specialized agents:")
    print("1. Chat Agent - Collects basic patient information")
    print("2. Reasoning Agent - Analyzes symptoms and medical conditions")
    print("3. Extraction Agent - Structures conversation data into JSON format")
    print("\nCommands:")
    print("  Type your message normally")
    print("  'quit' - Exit and save data")
    print("  'status' - View current patient data")
    print("  'extract' - Run data extraction on current conversation")
    print("  'test' - Test Gemini API")
    print("")
    
    while True:
        user_input = input("Patient: ").strip()
        
        if user_input.lower() == 'quit':
            print("Session ended. Patient data has been saved.")
            wandb.finish()
            break
        
        if user_input.lower() == 'status':
            status = patient_hero.get_patient_status()
            print(f"Current Status: {json.dumps(status, indent=2)}")
            continue
            
        if user_input.lower() == 'extract':
            print("Running data extraction on current conversation...")
            extraction_result = patient_hero._extract_structured_data()
            print(f"Extraction Result: {json.dumps(extraction_result, indent=2)}")
            continue
            
        if user_input.lower() == 'test':
            print("Testing Gemini API...")
            test_messages = [
                {"role": "system", "content": "You are a helpful medical assistant."},
                {"role": "user", "content": "Say hello and confirm you can process medical information."}
            ]
            test_result = patient_hero.run_llm_chat(test_messages, "test")
            print(f"✅ API Test Result: {test_result}")
            continue
        
        if user_input:
            try:
                response = patient_hero.process_user_input(user_input)
                
                # Display agent response with better formatting
                agent_name = response['agent'].replace('_', ' ').title()
                print(f"\n{agent_name}: {response['response']}\n")
                
                # Show extraction data if available
                if 'extraction_data' in response:
                    print("📊 Extracted Data Summary:")
                    extraction_data = response['extraction_data']
                    if 'personal_info' in extraction_data:
                        print(f"Personal Info Confidence: {extraction_data.get('extraction_confidence', {}).get('personal_info_confidence', 'unknown')}")
                    if 'medical_info' in extraction_data:
                        print(f"Medical Info Confidence: {extraction_data.get('extraction_confidence', {}).get('medical_info_confidence', 'unknown')}")
                    print(f"Overall Completeness: {extraction_data.get('extraction_confidence', {}).get('overall_completeness', 'unknown')}\n")
                
                # Show current status
                if response['next_step'] == 'continue_basic_info':
                    print(f"🔄 Status: Collecting basic information...")
                elif response['next_step'] == 'reasoning_analysis':
                    print(f"🧠 Status: Basic info complete - Now analyzing symptoms...")
                elif response['next_step'] == 'continue_symptom_analysis':
                    print(f"🩺 Status: Continuing symptom analysis...")
                
                print(f"Next Step: {response['next_step']}\n")
                
            except Exception as e:
                print(f"Error: {e}")
                continue

    
    def search_nearby_institutions(self, medical_condition: str, zip_code: str, insurance: str = None) -> list:
        """Search for nearby hospitals/institutions using ExaHelper (.org/.gov only)."""
        medical_data = {
            "medical_condition": medical_condition,
            "zip_code": zip_code,
            "insurance": insurance or "",
            "phone_suffix": "0000",
            "session_id": self.patient_data.session_id,
            "timestamp": datetime.now().isoformat()
        }
        return self.exa_helper.process_patient_from_main(medical_data)
