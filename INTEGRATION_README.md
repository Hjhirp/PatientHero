# PatientHero - AI Medical Consultation Platform

A full-stack healthcare application that combines CrewAI agents with a modern Next.js frontend to provide intelligent medical consultations.

## 🏗️ Architecture

```
┌─────────────────┐    HTTP/JSON     ┌──────────────────┐
│   Next.js       │ ◄──────────────► │   FastAPI        │
│   Frontend      │                  │   Backend        │
│   (Port 3000)   │                  │   (Port 8000)    │
└─────────────────┘                  └──────────────────┘
                                               │
                                               ▼
                                     ┌──────────────────┐
                                     │   CrewAI Agents  │
                                     │   - Chat Agent   │
                                     │   - Reasoning    │
                                     │   - Extraction   │
                                     └──────────────────┘
                                               │
                                               ▼
                                     ┌──────────────────┐
                                     │   ExaHelper      │
                                     │   (Exa.ai API)   │
                                     └──────────────────┘
```

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Clone and navigate to the project
cd PatientHero

# Run the automated setup
./setup_environment.sh
```

### 2. Configure API Keys

Edit the `.env` file with your API keys:

```env
GEMINI_API_KEY=your_actual_gemini_api_key
EXA_API_KEY=your_actual_exa_api_key
WANDB_API_KEY=your_wandb_api_key  # Optional
```

### 3. Test Setup

```bash
./test_setup.py
```

### 4. Start the Application

```bash
# Start both frontend and backend
./start_patienthero.sh
```

The application will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🎯 Features

### Frontend (Next.js)
- **Modern Chat Interface**: Clean, responsive medical consultation UI
- **Real-time Progress Tracking**: Visual progress indicator for information collection
- **Agent Identification**: Shows which CrewAI agent is responding
- **Session Management**: Persistent conversation sessions
- **HIPAA-Compliant Design**: Privacy-focused interface

### Backend (FastAPI + CrewAI)
- **Multi-Agent System**: 
  - **Chat Agent**: Collects basic patient information
  - **Reasoning Agent**: Analyzes symptoms and medical conditions
  - **Extraction Agent**: Structures conversation data
- **ExaHelper Integration**: Finds nearby medical institutions
- **Session Persistence**: Maintains conversation state
- **RESTful API**: Easy integration with any frontend

### AI Capabilities
- **Natural Conversation Flow**: Gradual information collection
- **Medical Reasoning**: Symptom analysis and preliminary assessment
- **Hospital Discovery**: Exa.ai integration for finding .org/.gov medical facilities
- **Insurance Validation**: Checks insurance acceptance at hospitals
- **Data Extraction**: Intelligent parsing of medical information

## 📊 API Endpoints

### Chat API
```
POST /api/chat
{
  "user_input": "I have a headache",
  "session_id": "optional_session_id"
}
```

### Status Check
```
GET /api/status/{session_id}
```

### Institution Search
```
POST /api/institutions/{session_id}
{
  "medical_condition": "headache",
  "zip_code": "12345",
  "insurance": "Blue Cross"
}
```

## 🔧 Development

### Running Components Separately

**Backend Only:**
```bash
cd PatientHero
source venv/bin/activate
python api_server.py
```

**Frontend Only:**
```bash
cd PatientHero
npm run dev
```

### Project Structure

```
PatientHero/
├── app/                    # Next.js app directory
│   ├── api/chat/          # Chat API route
│   ├── page.tsx           # Main chat interface
│   └── layout.tsx         # App layout
├── components/            # React components
├── crewai_agents/        # CrewAI Python agents
│   ├── main.py           # PatientHeroCrewAI class
│   ├── exa_helper.py     # Exa.ai integration
│   └── *.json            # Patient data files
├── api_server.py         # FastAPI backend server
├── start_patienthero.sh  # Startup script
└── setup_environment.sh  # Environment setup
```

## 🔐 Security & Privacy

- **Data Isolation**: Each patient session is isolated
- **No Persistent Storage**: Patient data is only kept in memory during sessions
- **API Key Protection**: Sensitive keys are server-side only
- **CORS Configuration**: Restricted to localhost in development

## 🛠️ Troubleshooting

### Backend Connection Issues
1. Check if FastAPI server is running on port 8000
2. Verify API keys are set in `.env`
3. Ensure Python dependencies are installed

### Frontend Issues
1. Check if Next.js is running on port 3000
2. Verify Node.js dependencies are installed
3. Check browser console for errors

### CrewAI Agent Issues
1. Verify Gemini API key is valid
2. Check Wandb authentication (optional)
3. Review agent logs in terminal

## 📝 Example Conversation Flow

1. **Patient**: "Hi, I have a headache"
2. **Chat Agent**: "I understand you're experiencing a headache. To help you better, could you provide your ZIP code?"
3. **Patient**: "12345"
4. **Chat Agent**: "Thank you. Could you please share your phone number for contact purposes?"
5. **Patient**: "555-123-4567"
6. **Chat Agent**: "What insurance do you have?"
7. **Patient**: "Blue Cross Blue Shield"
8. **System**: ✅ Basic information complete! Switching to symptom analysis...
9. **Reasoning Agent**: "Now I'd like to understand your headache better. How long have you been experiencing this? On a scale of 1-10, how would you rate the pain?"

## 🔮 Future Enhancements

- **Database Integration**: Persistent patient data storage
- **Authentication**: User accounts and login system
- **Appointment Booking**: Integration with hospital scheduling systems
- **Telemedicine**: Video consultation capabilities
- **Mobile App**: React Native or Flutter mobile client
- **Multi-language**: Support for multiple languages

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 🙋‍♀️ Support

For questions or issues:
1. Check the troubleshooting section
2. Review the API documentation at `/docs`
3. Open an issue on GitHub
4. Check CrewAI and Exa.ai documentation
