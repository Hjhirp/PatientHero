# PatientHero CrewAI Agents with Data Extraction

This directory contains a comprehensive implementation of three CrewAI agents with Wandb Weave monitoring for PatientHero medical consultation system.

## Overview

The system consists of three specialized agents:

1. **Chat Agent (Patient Information Collector)**: Collects basic patient information including medical condition, zip code, phone number, and insurance details.

2. **Reasoning Agent (Medical Reasoning Specialist)**: Analyzes patient's medical condition and dives deeper into possible symptoms and related health concerns.

3. **Extraction Agent (Data Extraction Specialist)** ⭐ **NEW**: Extracts and structures all patient information from conversation data into standardized JSON format with confidence scoring.

## Features

- **Custom Gemini LLM Integration**: Custom CrewAI LLM class for seamless Google Gemini API integration
- **Wandb Weave Integration**: Comprehensive monitoring of agent communications and interactions
- **Google Gemini API**: Uses Google's Gemini 1.5 Flash model for intelligent responses
- **Sequential Processing**: Chat agent collects basic info first, then reasoning agent performs analysis, followed by data extraction
- **Structured JSON Output**: All patient data is extracted and stored in standardized JSON format for pipeline integration
- **Confidence Scoring**: Quality assessment of extracted data with high/medium/low confidence levels
- **Real-time Extraction**: Data structured during conversation flow
- **Conversation History**: Complete conversation tracking
- **Error Handling**: Robust error handling and validation with API fallbacks
- **Traced LLM Calls**: All model interactions are traced with Weave for monitoring and debugging

## Setup

### Option 1: Automated Setup (Recommended)
```bash
chmod +x setup.sh
./setup.sh
```
This script will automatically detect if you have conda installed and create the appropriate environment.

### Option 2: Manual Conda Setup
```bash
# Create environment from file
conda env create -f environment.yml

# Or create manually
conda create -n patienthero-crewai python=3.11 -y
conda activate patienthero-crewai
pip install -r requirements.txt
```

### Option 3: Virtual Environment (Fallback)
```bash
python -m venv patienthero-crewai-venv
source patienthero-crewai-venv/bin/activate
pip install -r requirements.txt
```

### Configure Environment Variables
Edit `.env` file with your API keys:
```bash
# W&B API Key for logging and monitoring (Get from https://wandb.ai/authorize)
WANDB_API_KEY=your_wandb_api_key_here
WANDB_PROJECT=patienthero-crewai
WANDB_ENTITY=your_wandb_entity_here

# Google Gemini API Key (Primary - Get from https://aistudio.google.com/app/apikey)
GEMINI_API_KEY=your_gemini_api_key_here

# OpenAI API Key (Backup/Alternative)
OPENAI_API_KEY=your_openai_api_key_here

# Data storage paths
DATA_OUTPUT_PATH=./patient_data.json
EXTRACTED_DATA_OUTPUT_PATH=./extracted_patient_data.json
```

**Note**: The system now uses **Google Gemini API** with the **Gemini 1.5 Flash** model. 

**Important**: 
- Get your Gemini API key from https://aistudio.google.com/app/apikey
- The system offers fast, intelligent responses with a 32K context window
- W&B is used for monitoring and logging, not for LLM inference

### Activate Environment
```bash
# For conda
conda activate patienthero-crewai

# For virtual environment
source patienthero-crewai-venv/bin/activate
```

## Usage

### Running the Interactive System

```bash
python main.py
```

### Running Tests

```bash
python test_agents.py
```

### Example Conversation Flow

1. **Initial Contact**: Patient describes their medical condition
2. **Information Collection**: Chat agent gathers zip code, phone, insurance
3. **Symptom Analysis**: Reasoning agent analyzes condition and explores symptoms
4. **Data Storage**: All information saved to JSON file

## Data Structure

Patient data is stored in the following JSON format:

```json
{
  "session_id": "unique-session-id",
  "timestamp": "2025-01-13T10:00:00",
  "medical_condition": "severe back pain",
  "zip_code": "90210",
  "phone_number": "555-123-4567",
  "insurance": "Blue Cross Blue Shield",
  "symptoms": ["lower back pain", "pain when sitting"],
  "reasoning_analysis": "Detailed analysis from reasoning agent",
  "conversation_history": [
    {
      "timestamp": "2025-01-13T10:00:00",
      "speaker": "user",
      "message": "I have severe back pain"
    }
  ]
}
```

## Wandb Weave Monitoring

The system tracks:

- **Agent Interactions**: Input/output for each agent
- **Conversation Flow**: Complete conversation tracking
- **Data Completion Status**: Progress tracking
- **Session Analytics**: Performance metrics

## File Structure

```
crewai_agents/
├── main.py              # Main system implementation
├── test_agents.py       # Test scenarios
├── setup.sh            # Setup script
├── requirements.txt    # Python dependencies
├── .env.example       # Environment template
├── README.md          # This file
└── patient_data.json  # Generated data storage
```

## Key Classes

- **`PatientData`**: Data structure for patient information
- **`WandbWeaveMonitor`**: Monitoring and logging functionality
- **`PatientHeroCrewAI`**: Main orchestration class

## Workflow

1. User input is processed through the chat agent first
2. Basic information (condition, zip, phone, insurance) is collected
3. Once basic info is complete, reasoning agent takes over
4. Reasoning agent performs symptom analysis and medical reasoning
5. All interactions are logged to Wandb Weave
6. Patient data is saved to JSON file

## Customization

- **Agent Prompts**: Modify agent backstories in `_create_agents()`
- **Data Fields**: Add fields to `PatientData` class
- **NLP Processing**: Enhance `_update_patient_data_from_input()` method
- **Monitoring**: Customize Wandb logging in `WandbWeaveMonitor` class

## Production Considerations

- Replace simple regex parsing with advanced NLP
- Add input validation and sanitization
- Implement proper error recovery
- Add authentication and session management
- Scale with database storage instead of JSON files
- Add HIPAA compliance measures

## Architecture

### Custom Gemini LLM Integration

The system uses a custom `GeminiLLM` class that extends CrewAI's `BaseLLM` to integrate directly with the Google Gemini API:

```python
class GeminiLLM(BaseLLM):
    """Custom LLM class for Google Gemini API integration with CrewAI"""
    
    def __init__(self, model: str, api_key: str, temperature: Optional[float] = 0.7):
        super().__init__(model=model, temperature=temperature)
        self.api_key = api_key
        self.model_name = model
        genai.configure(api_key=api_key)
        
    def call(self, messages, tools=None, callbacks=None, available_functions=None, **kwargs):
        # Convert messages to Gemini format and make API call
        model = genai.GenerativeModel(self.model_name)
        response = model.generate_content(prompt, generation_config=config)
        return response.text
```

### Correct Gemini API Usage Format:

```python
import google.generativeai as genai

genai.configure(api_key="your_gemini_api_key")
model = genai.GenerativeModel('gemini-1.5-flash')
response = model.generate_content("Your prompt here")
```

**Benefits:**
- ✅ Direct integration with Google Gemini API
- ✅ Fast and intelligent responses with Gemini 1.5 Flash
- ✅ Built-in error handling and fallbacks  
- ✅ Support for function calling and tools
- ✅ Seamless CrewAI compatibility
- ✅ Large context window (32K tokens)
- ✅ Cost-effective and reliable
