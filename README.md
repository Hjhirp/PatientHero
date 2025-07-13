# PatientHero - Complete AI Healthcare Assistant

A comprehensive healthcare consultation platform that combines a modern ChatGPT-style interface with intelligent AI agents for medical information collection, symptom analysis, hospital search, appointment processing, and patient support throughout their healthcare journey.

## 🌟 Features

### Core Functionality
- **🤖 Multi-Agent AI System**: Three specialized CrewAI agents for different phases of patient care
- **💬 Intelligent Chat Interface**: Natural conversation flow with context-aware responses
- **🏥 Hospital Discovery**: Automated search for nearby medical institutions using Exa.ai
- **📅 Appointment Processing**: Parallel processing of hospital websites to find available slots
- **🛣️ Journey Support**: Comfort guidance and reassurance during travel to hospital
- **📊 Data Extraction**: Structured JSON output for seamless integration with other systems
- **🔄 Background Processing**: Non-blocking appointment scraping and data processing

### Technical Features
- **🎨 Modern UI**: Clean, responsive design with dark/light theme support
- **� Mobile Responsive**: Works perfectly on all device sizes
- **⚡ Real-time Processing**: Live updates and background task management
- **🔒 Session Management**: Persistent sessions with conversation history
- **📈 Monitoring**: Comprehensive logging with W&B Weave integration
- **🛡️ Error Handling**: Robust error handling and graceful fallbacks

## 🏗️ Architecture

### AI Agent System (CrewAI)
```
┌─────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   Chat Agent    │    │ Reasoning Agent  │    │ Extraction Agent │
│ (Info Collect)  │ -> │ (Symptom Analys) │ -> │ (Data Structure) │
└─────────────────┘    └──────────────────┘    └──────────────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │     Gemini 2.5 Flash     │
                    │    (Google AI API)       │
                    └───────────────────────────┘
```

### Data Flow
```
User Input -> Chat Agent -> Basic Info Complete? 
                              │
                              ├─ No: Continue Collection
                              │
                              └─ Yes: Hospital Search (Exa.ai)
                                      │
                                      ├─ Background: Appointment Processing
                                      │
                                      └─ Reasoning Agent -> Comfort Guidance
```

### Backend Services
- **FastAPI Server**: REST API with session management
- **CrewAI Agents**: Specialized AI agents for different tasks
- **Playwright**: Browser automation for appointment scraping
- **Exa.ai Integration**: Hospital and clinic discovery
- **W&B Weave**: AI interaction monitoring and tracing

## 🚀 Quick Start

### Prerequisites
- **Node.js 18+** 
- **Python 3.11+**
- **Google Gemini API Key**
- **W&B API Key** (for monitoring)
- **Exa.ai API Key** (for hospital search)

### 1. Clone and Setup
```bash
git clone <repository-url>
cd PatientHero

# Install frontend dependencies
npm install

# Setup Python environment
cd crewai_agents
chmod +x setup.sh
./setup.sh

# Install Playwright browsers
conda activate patienthero-crewai
playwright install
```

### 2. Environment Configuration
Create `.env` files with your API keys:

**Root `.env`:**
```bash
GEMINI_API_KEY=your_gemini_api_key
WANDB_API_KEY=your_wandb_api_key
WANDB_PROJECT=patienthero-crewai
WANDB_ENTITY=your_wandb_entity
EXA_API_KEY=your_exa_api_key
```

**`crewai_agents/.env`:**
```bash
GEMINI_API_KEY=your_gemini_api_key
WANDB_API_KEY=your_wandb_api_key
WANDB_PROJECT=patienthero-crewai
WANDB_ENTITY=your_wandb_entity
EXA_API_KEY=your_exa_api_key
```

### 3. Start the Services
```bash
# Terminal 1: Start the API server
python api_server.py

# Terminal 2: Start the frontend
npm run dev
```

### 4. Access the Application
- **Frontend**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000

## 📋 Complete User Flow

### Phase 1: Information Collection
1. **User starts conversation** with greeting
2. **Chat Agent activates** to collect:
   - Medical condition/symptoms
   - ZIP code for location
   - Phone number for contact
   - Insurance information

### Phase 2: Hospital Discovery & Appointment Processing
3. **Automatic hospital search** using Exa.ai
4. **Background appointment processing** with Playwright
5. **Data structure extraction** with confidence scoring

### Phase 3: Medical Reasoning & Support
6. **Reasoning Agent analysis** of symptoms and conditions
7. **Comfort guidance provision** (2 rounds of support)
8. **Journey assistance** with practical tips

## 🛠️ Tech Stack

### Frontend
- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: Radix UI primitives
- **Icons**: Lucide React
- **State Management**: React hooks and context
- **Theme**: next-themes for dark/light mode

### Backend
- **API Framework**: FastAPI
- **AI Framework**: CrewAI with custom Gemini LLM
- **Language Model**: Google Gemini 2.5 Flash
- **Browser Automation**: Playwright
- **Search Engine**: Exa.ai API
- **Monitoring**: W&B Weave
- **Session Storage**: In-memory (production: Redis/DB)

### Development Tools
- **Package Management**: npm, conda/pip
- **Code Quality**: ESLint, Prettier
- **Type Checking**: TypeScript
- **API Documentation**: FastAPI auto-docs

## 📁 Project Structure

```
PatientHero/
├── app/                    # Next.js 14 app directory
│   ├── globals.css        # Global styles and themes
│   ├── layout.tsx         # Root layout with providers
│   └── page.tsx           # Main chat interface
├── components/            # React components
│   ├── ui/               # Reusable UI primitives
│   ├── providers/        # Context providers
│   ├── medical-consultation.tsx  # Main chat component
│   ├── appointment-flow.tsx      # Appointment processing UI
│   ├── sidebar.tsx       # Navigation sidebar
│   └── theme-toggle.tsx  # Dark/light mode toggle
├── lib/                  # Utility functions and services
│   ├── ai-service.ts     # API communication layer
│   ├── utils.ts          # Helper functions
│   └── hooks.ts          # Custom React hooks
├── crewai_agents/        # AI agent system
│   ├── main.py           # Core CrewAI implementation
│   ├── exa_helper.py     # Hospital search integration
│   ├── requirements.txt  # Python dependencies
│   ├── environment.yml   # Conda environment
│   └── setup.sh          # Automated setup script
├── api_server.py         # FastAPI backend server
├── process_clinics_parallel.py  # Appointment processing
├── docs/                 # Documentation
│   ├── DEPLOYMENT_GUIDE.md
│   ├── PROMPT_SYSTEM.md
│   └── WANDB_SUMMARY.md
└── scripts/              # Utility scripts
```

## 🔧 API Endpoints

### Core Chat API
- `POST /api/chat` - Process user input through AI agents
- `GET /api/status/{session_id}` - Get session status and patient data

### Appointment System
- `POST /api/complete-flow/{session_id}` - Full medical flow processing
- `GET /api/appointments/{session_id}` - Get processed appointment data
- `POST /api/appointments/process` - Manual appointment processing

### Patient Support
- `GET /api/comfort-guidance/{session_id}` - Comfort guidance rounds
- `POST /api/sessions/{session_id}/end` - End patient session

### Monitoring
- `GET /api/sessions` - List active sessions (debug)
- `GET /` - API health check

## 💾 Data Models

### Patient Data Structure
```typescript
interface PatientData {
  session_id: string;
  timestamp: string;
  medical_condition?: string;
  zip_code?: string;
  phone_number?: string;
  insurance?: string;
  symptoms?: string[];
  reasoning_analysis?: string;
  conversation_history: ConversationEntry[];
}
```

### Appointment Data Structure
```typescript
interface AppointmentData {
  hospital_name: string;
  website: string;
  institution_type: string;
  accepts_user_insurance: string;
  appointment_availability: {
    available_slots: AppointmentSlot[];
    total_slots_found: number;
    next_available: string;
    booking_method: string;
  };
}
```

## 🔄 Agent Workflows

### 1. Chat Agent (Information Collector)
- **Role**: Friendly medical intake specialist
- **Goal**: Collect essential patient information naturally
- **Behavior**: One question at a time, empathetic responses
- **Transition**: Switches to Reasoning Agent when basic info complete

### 2. Reasoning Agent (Medical Analysis)
- **Role**: Medical reasoning specialist
- **Goal**: Analyze symptoms and provide preliminary guidance
- **Behavior**: Evidence-based analysis, follow-up questions
- **Output**: Detailed symptom analysis and medical reasoning

### 3. Extraction Agent (Data Structuring)
- **Role**: Data extraction specialist
- **Goal**: Structure conversation data into JSON format
- **Behavior**: Intelligent parsing, confidence scoring
- **Output**: Structured patient data with metadata

## 🏥 Hospital Processing

### Exa.ai Integration
- **Search scope**: .org and .gov domains only
- **Filters**: Location-based, insurance compatibility
- **Output**: Structured hospital data with contact information

### Appointment Processing
- **Method**: Parallel Playwright browser automation
- **Target**: Hospital booking pages and forms
- **Extraction**: Available time slots, booking methods
- **Performance**: Concurrent processing for speed

### Data Cleaning
- **Standardization**: Consistent appointment slot formats
- **Validation**: Remove invalid or malformed data
- **Enhancement**: Add booking methods and availability status

## 📊 Monitoring & Analytics

### W&B Weave Integration
- **Agent Interactions**: Every AI model call traced
- **Session Tracking**: Complete conversation flows
- **Performance Metrics**: Response times, success rates
- **Error Tracking**: Detailed error logs and context

### Key Metrics
- **Information Collection Rate**: Percentage of complete patient profiles
- **Agent Transition Success**: Chat -> Reasoning -> Extraction flow
- **Appointment Processing**: Success rate of hospital data extraction
- **User Engagement**: Session duration and interaction quality

## 🔒 Security & Privacy

### Data Protection
- **Session Isolation**: Each session independent and secure
- **Temporary Storage**: Patient data not permanently stored
- **API Security**: CORS protection and request validation
- **Privacy**: No data sharing with external services (except AI APIs)

### Safety Measures
- **Content Filtering**: Gemini safety settings configured
- **Error Boundaries**: Graceful handling of API failures
- **Input Validation**: Sanitization of user inputs
- **Rate Limiting**: Protection against abuse

## 🚀 Deployment Options

### Development (Local)
```bash
# Start both services locally
python api_server.py &
npm run dev
```

### Production (Recommended)
- **Frontend**: Vercel, Netlify, or similar
- **Backend**: Railway, Render, or VPS
- **Database**: PostgreSQL or MongoDB for persistence
- **Monitoring**: W&B dashboard for production monitoring

### Docker Deployment
```bash
# Build and run with Docker
docker build -t patienthero .
docker run -p 3000:3000 -p 8000:8000 patienthero
```

## 🧪 Testing

### Frontend Testing
```bash
npm run test          # Run test suite
npm run test:watch    # Watch mode
npm run lint          # Code quality check
```

### Backend Testing
```bash
cd crewai_agents
python test_complete_flow.py  # Test complete AI flow
python -m pytest tests/       # Run unit tests
```

### API Testing
```bash
# Test core endpoints
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Hi, I have a fever", "session_id": "test-123"}'

curl -X POST http://localhost:8000/api/complete-flow/test-123
```

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Set up development environment
4. Make your changes
5. Add tests if applicable
6. Submit a pull request

### Code Style
- **Frontend**: ESLint + Prettier configuration
- **Backend**: PEP 8 Python style guide
- **Commits**: Conventional commit messages
- **Documentation**: Update README for significant changes

## 📞 Healthcare Disclaimer

**Important**: This application is designed for educational and demonstration purposes. It should not be used as a substitute for professional medical advice, diagnosis, or treatment. Always consult with qualified healthcare providers for medical concerns.

## 🔮 Future Enhancements

### Planned Features
- [ ] **User Authentication**: Persistent user accounts
- [ ] **Database Integration**: Long-term data storage
- [ ] **Real Appointment Booking**: Direct integration with hospital systems
- [ ] **Telemedicine**: Video consultation capabilities
- [ ] **Multi-language**: Support for multiple languages
- [ ] **Mobile App**: Native iOS/Android applications

### AI Improvements
- [ ] **Memory Enhancement**: Long-term conversation memory
- [ ] **Specialized Models**: Domain-specific medical AI models
- [ ] **Voice Interface**: Speech-to-text and text-to-speech
- [ ] **Predictive Analytics**: Early symptom detection
- [ ] **Personalization**: Adaptive responses based on user history

### Integration Opportunities
- [ ] **EHR Systems**: Electronic health record integration
- [ ] **Insurance APIs**: Real-time coverage verification
- [ ] **Pharmacy Systems**: Prescription management
- [ ] **Wearable Devices**: Health data integration
- [ ] **Emergency Services**: Direct 911/emergency routing

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **CrewAI**: Multi-agent AI framework
- **Google Gemini**: Advanced language model capabilities
- **Exa.ai**: Intelligent web search for healthcare
- **W&B Weave**: AI application monitoring and tracing
- **Radix UI**: Accessible component primitives
- **Playwright**: Reliable browser automation

---

## 📚 Additional Documentation

- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) - Detailed deployment instructions
- [Prompt System Documentation](docs/PROMPT_SYSTEM.md) - AI agent prompt engineering
- [W&B Integration Guide](docs/WANDB_SUMMARY.md) - Monitoring and analytics setup
- [API Documentation](http://localhost:8000/docs) - Interactive API documentation

## 🆘 Support

For technical support, bug reports, or feature requests:
1. Check existing [Issues](../../issues)
2. Create a new issue with detailed description
3. Include environment details and error logs
4. Tag with appropriate labels

---

**Built with ❤️ for better healthcare accessibility**
│   ├── ui/               # Reusable UI components
│   ├── providers/        # Context providers
│   ├── sidebar.tsx       # Chat sidebar
│   └── theme-toggle.tsx  # Theme switcher
├── lib/                  # Utility functions
│   └── utils.ts          # Helper functions
├── public/               # Static assets
│   └── manifest.json     # PWA manifest
└── types/                # TypeScript type definitions
```

## Key Components

### Chat Interface
- **Message Display**: Shows user and AI messages with timestamps
- **Real-time Input**: Send messages with Enter key or button click
- **Typing Indicators**: Visual feedback when AI is responding
- **Message History**: Persistent chat history across sessions

### Sidebar Navigation
- **Chat List**: Organized by date (Today, Yesterday, Previous 7 days, Older)
- **New Chat**: Create new conversations
- **Search**: Filter chats by title
- **Responsive**: Collapsible on mobile devices

### Theme System
- **Dark/Light Mode**: Toggle between themes
- **System Preference**: Respects user's system theme
- **Persistent**: Theme preference saved locally

## Customization

### Styling
The app uses Tailwind CSS with a custom color system. You can modify the theme in:
- `tailwind.config.js` - Tailwind configuration
- `app/globals.css` - CSS custom properties for colors

### AI Integration
To connect to actual AI services, modify the `sendMessage` function in `app/page.tsx`:

```typescript
// Replace the simulation with actual AI API calls
const sendMessage = async () => {
  // Your AI API integration here
}
```

### Components
All UI components are in the `components/ui/` directory and are built with Radix UI primitives for accessibility and customization.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Healthcare Disclaimer

This application is designed for educational and demonstration purposes. It should not be used as a substitute for professional medical advice, diagnosis, or treatment. Always consult with qualified healthcare providers for medical concerns.

## Implementation Status

### ✅ Completed Features

- [x] Modern Next.js 14 + TypeScript setup
- [x] Responsive chat interface with sidebar
- [x] Dark/light theme toggle
- [x] Message input with auto-resize textarea
- [x] Chat history management
- [x] Loading states and animations
- [x] Settings dialog
- [x] PWA configuration with manifest
- [x] Modern UI components (Button, Input, Card, Avatar, etc.)
- [x] Proper favicon and app icons
- [x] TypeScript type safety
- [x] Tailwind CSS styling
- [x] Radix UI component primitives
- [x] **Med42-8B Integration**: Production-ready medical AI on Fly.io
- [x] **AI Service Layer**: OpenAI-compatible API for seamless integration
- [x] **Medical Specialization**: Healthcare-focused prompts and responses

### 🚧 In Progress / Next Steps

- [ ] **Deploy Med42-8B**: Run `cd fly-llm-server && ./deploy.sh` for cloud deployment
- [ ] User authentication
- [ ] Database integration for chat persistence
- [ ] Message export functionality
- [ ] File upload support
- [ ] Voice input/output
- [ ] Medical data integration
- [ ] Advanced settings (model parameters)
- [ ] Chat sharing and collaboration
- [ ] Analytics and usage tracking

### 💡 Future Enhancements

- [ ] Multi-language support
- [ ] Plugin system for medical tools
- [ ] Integration with EHR systems
- [ ] Appointment scheduling
- [ ] Medication reminders
- [ ] Health data visualization
- [ ] Telemedicine integration

## Current Status

The application is **production-ready** with complete AI integration! 

### 🤖 AI Integration Status
- ✅ **Med42-8B Integration**: Production-ready medical AI on Fly.io
- ✅ **OpenAI-Compatible API**: Seamless integration with standard formats
- ✅ **Medical Specialization**: Healthcare-focused system prompts
- ✅ **Scalable Deployment**: Auto-scaling GPU infrastructure on Fly.io

### 🚀 Quick Start Options

**Production Deployment (Recommended)**
```bash
cd fly-llm-server && ./deploy.sh  # Deploy Med42-8B to Fly.io
npm run dev                       # Start the frontend
```

### 📊 Deployment Comparison

| Feature | Med42-8B on Fly.io | Local Setup |
|---------|-------------------|-------------|
| **Cost** | $50-150/month (scales to $0) | Free |
| **Setup Time** | 15 minutes | N/A |
| **Performance** | Very Fast (A10 GPU) | N/A |
| **Privacy** | Secure Cloud | N/A |
| **Maintenance** | Managed | N/A |

### Next Steps
1. **Deploy Med42-8B**: Follow the deployment guide in `fly-llm-server/DEPLOYMENT.md`
2. **Configure environment**: Update `.env.local` with your Fly.io URL
3. **Test integration**: Ensure the frontend connects to your deployed backend
4. **Add authentication**: For user management and chat persistence

The UI is production-ready and follows modern design patterns. All core components are implemented and the application is responsive across all device sizes.