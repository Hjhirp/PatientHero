import { NextRequest, NextResponse } from 'next/server'
import { PatientHeroGuardrails } from '@/lib/weave-guardrails'

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

interface ChatResponse {
  success: boolean
  data?: CrewAIResponse
  error?: string
  guardrail_warning?: string
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

export async function POST(request: NextRequest): Promise<NextResponse<ChatResponse>> {
  try {
    const body = await request.json()
    const { message, sessionId } = body

    if (!message) {
      return NextResponse.json(
        { success: false, error: 'Message is required' },
        { status: 400 }
      )
    }

    // Initialize guardrails
    const guardrails = PatientHeroGuardrails.getInstance()
    
    // Validate user input first
    const inputValidation = await guardrails.validateUserInput(message)
    if (!inputValidation.allowed) {
      console.log(`🚨 Guardrail blocked user input: ${inputValidation.reason}`)
      
      return NextResponse.json({
        success: true,
        data: {
          agent: 'guardrail_system',
          response: "I notice your message contains content that I can't process. Please rephrase your message and ensure it's related to your healthcare needs.",
          patient_data: { 
            session_id: sessionId || `session_${Date.now()}`,
            conversation_history: []
          },
          next_step: 'continue_basic_info'
        },
        guardrail_warning: inputValidation.reason
      })
    }

    // Call CrewAI backend
    const crewAIResponse = await callCrewAIBackend(message, sessionId)

    // Validate AI response with guardrails
    const responseValidation = await guardrails.validateAIResponse(
      crewAIResponse.response, 
      message
    )
    
    if (!responseValidation.allowed) {
      console.log(`🚨 Guardrail blocked AI response: ${responseValidation.reason}`)
      
      // Replace with safe fallback response
      crewAIResponse.response = "I apologize, but I need to rephrase my response. Could you please tell me more about your healthcare needs so I can assist you better?"
      crewAIResponse.agent = 'guardrail_system'
    }

    return NextResponse.json({
      success: true,
      data: crewAIResponse,
      guardrail_warning: !responseValidation.allowed ? responseValidation.reason : undefined
    })

  } catch (error) {
    console.error('Chat API error:', error)
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
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
