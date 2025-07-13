import { NextRequest, NextResponse } from 'next/server'

interface ChatMessage {
  message: string
  timestamp: string
}

interface PatientData {
  session_id: string
  medical_condition?: string
  zip_code?: string
  phone_number?: string
  insurance?: string
  symptoms?: string[]
  reasoning_analysis?: string
  conversation_history: ChatMessage[]
}

interface CrewAIResponse {
  agent: string
  response: string
  patient_data: PatientData
  next_step: string
  extraction_data?: any
}

// Connect to your CrewAI Python backend
async function callCrewAIBackend(userInput: string, sessionId?: string): Promise<CrewAIResponse> {
  const backendUrl = process.env.CREWAI_BACKEND_URL || 'http://localhost:8000'
  
  try {
    console.log(`Calling CrewAI backend at ${backendUrl}/api/chat`)
    
    const response = await fetch(`${backendUrl}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_input: userInput,
        session_id: sessionId
      })
    })
    
    if (!response.ok) {
      throw new Error(`CrewAI backend error: ${response.status} ${response.statusText}`)
    }
    
    const data = await response.json()
    return data
  } catch (error) {
    console.error('CrewAI backend connection failed:', error)
    // Fallback simulation for development
    console.log('Using fallback simulation - CrewAI backend not available')
    return simulateCrewAIResponse(userInput, sessionId)
  }
}

function simulateCrewAIResponse(userInput: string, sessionId?: string): CrewAIResponse {
  const currentSessionId = sessionId || `session_${Date.now()}`
  
  // Simulate different agent responses based on conversation state
  const hasBasicInfo = userInput.includes('insurance') || userInput.includes('phone') || 
                      userInput.includes('zip') || /\d{5}/.test(userInput)
  
  if (!hasBasicInfo) {
    return {
      agent: 'chat_agent',
      response: `Hello! I'm here to help you with your healthcare needs. To get started, could you tell me what medical condition or symptoms are you experiencing today?`,
      patient_data: {
        session_id: currentSessionId,
        conversation_history: [
          {
            message: userInput,
            timestamp: new Date().toISOString()
          }
        ]
      },
      next_step: 'continue_basic_info'
    }
  } else {
    return {
      agent: 'reasoning_agent',
      response: `Thank you for providing that information. Based on what you've shared, I'd like to understand your symptoms better. Can you describe the severity and duration of your condition? This will help me provide better guidance.`,
      patient_data: {
        session_id: currentSessionId,
        medical_condition: 'Patient condition from input',
        conversation_history: [
          {
            message: userInput,
            timestamp: new Date().toISOString()
          }
        ]
      },
      next_step: 'reasoning_analysis'
    }
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { message, sessionId } = body

    if (!message) {
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      )
    }

    // Call CrewAI backend
    const crewAIResponse = await callCrewAIBackend(message, sessionId)

    return NextResponse.json({
      success: true,
      data: crewAIResponse
    })

  } catch (error) {
    console.error('Chat API error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function GET() {
  return NextResponse.json({
    status: 'PatientHero Chat API is running',
    timestamp: new Date().toISOString()
  })
}
