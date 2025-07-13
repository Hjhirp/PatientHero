'use client'

import { useState, useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Loader2, Send, User, Bot, Heart, Clock } from 'lucide-react'
import { toast } from 'sonner'

interface Message {
  id: string
  content: string
  sender: 'user' | 'assistant'
  timestamp: Date
  agent?: string
}

interface PatientData {
  session_id: string
  medical_condition?: string
  zip_code?: string
  phone_number?: string
  insurance?: string
  symptoms?: string[]
  reasoning_analysis?: string
}

interface ChatResponse {
  agent: string
  response: string
  patient_data: PatientData
  next_step: string
  extraction_data?: any
}

export default function PatientHeroChat() {
  const [mounted, setMounted] = useState(false)
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      content: 'Hello! I\'m your PatientHero AI assistant. I\'m here to help you with your healthcare needs. To get started, could you tell me what brings you in today?',
      sender: 'assistant',
      timestamp: new Date(),
      agent: 'chat_agent'
    }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [patientData, setPatientData] = useState<PatientData | null>(null)
  const [nextStep, setNextStep] = useState('continue_basic_info')
  const scrollAreaRef = useRef<HTMLDivElement>(null)

  // Fix hydration issues
  useEffect(() => {
    setMounted(true)
  }, [])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight
    }
  }, [messages])

  const sendMessage = async (content: string) => {
    if (!content.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: content.trim(),
      sender: 'user',
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: content.trim(),
          sessionId: sessionId
        })
      })

      if (!response.ok) {
        throw new Error('Failed to send message')
      }

      const data = await response.json()
      const chatResponse: ChatResponse = data.data

      // Update session data
      if (!sessionId) {
        setSessionId(chatResponse.patient_data.session_id)
      }
      setPatientData(chatResponse.patient_data)
      setNextStep(chatResponse.next_step)

      // Add assistant response
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: chatResponse.response,
        sender: 'assistant',
        timestamp: new Date(),
        agent: chatResponse.agent
      }

      setMessages(prev => [...prev, assistantMessage])

      // Show progress notifications
      if (chatResponse.next_step === 'reasoning_analysis') {
        toast.success('Basic information collected! Moving to symptom analysis.')
      }

    } catch (error) {
      console.error('Error sending message:', error)
      toast.error('Failed to send message. Please try again.')
      
      // Add error message
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: 'I apologize, but I\'m having trouble connecting right now. Please try again in a moment.',
        sender: 'assistant',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    sendMessage(input)
  }

  const getAgentName = (agent?: string) => {
    switch (agent) {
      case 'chat_agent':
        return 'Information Collector'
      case 'reasoning_agent':
        return 'Medical Reasoning'
      case 'extraction_agent':
        return 'Data Specialist'
      default:
        return 'PatientHero AI'
    }
  }

  const getProgressPercentage = () => {
    if (!patientData) return 0
    const fields = ['medical_condition', 'zip_code', 'phone_number', 'insurance']
    const completed = fields.filter(field => patientData[field as keyof PatientData]).length
    return (completed / fields.length) * 100
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 dark:from-gray-900 dark:to-gray-800">
      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 max-w-7xl mx-auto">
          
          {/* Progress Sidebar */}
          <div className="lg:col-span-1 space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Heart className="h-5 w-5 text-red-500" />
                  PatientHero
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span>Information Progress</span>
                    <span>{Math.round(getProgressPercentage())}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-green-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${getProgressPercentage()}%` }}
                    />
                  </div>
                </div>
                
                {patientData && (
                  <div className="space-y-2">
                    <h4 className="font-medium text-sm">Collected Information:</h4>
                    <div className="space-y-1">
                      {patientData.medical_condition && (
                        <Badge variant="secondary" className="text-xs">
                          ✓ Medical Condition
                        </Badge>
                      )}
                      {patientData.zip_code && (
                        <Badge variant="secondary" className="text-xs">
                          ✓ ZIP Code
                        </Badge>
                      )}
                      {patientData.phone_number && (
                        <Badge variant="secondary" className="text-xs">
                          ✓ Phone Number
                        </Badge>
                      )}
                      {patientData.insurance && (
                        <Badge variant="secondary" className="text-xs">
                          ✓ Insurance
                        </Badge>
                      )}
                    </div>
                  </div>
                )}

                <div className="pt-4 border-t">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                    <Clock className="h-4 w-4" />
                    <span>Available 24/7</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Chat Interface */}
          <div className="lg:col-span-3">
            <Card className="h-[600px] flex flex-col">
              <CardHeader>
                <CardTitle>Medical Consultation Chat</CardTitle>
                <div className="flex items-center gap-2">
                  <Badge variant={nextStep === 'continue_basic_info' ? 'default' : 'secondary'}>
                    {nextStep === 'continue_basic_info' ? 'Collecting Info' : 
                     nextStep === 'reasoning_analysis' ? 'Analyzing Symptoms' : 
                     'Symptom Analysis'}
                  </Badge>
                  {sessionId && (
                    <Badge variant="outline" className="text-xs">
                      Session: {sessionId.slice(-8)}
                    </Badge>
                  )}
                </div>
              </CardHeader>
              
              <CardContent className="flex-1 flex flex-col p-0">
                <div className="flex-1 overflow-hidden p-6 pb-0">
                  <div className="h-full overflow-y-auto pr-4 space-y-4" ref={scrollAreaRef}>
                    {messages.map((message) => (
                      <div
                        key={message.id}
                        className={`flex gap-3 ${
                          message.sender === 'user' ? 'flex-row-reverse' : 'flex-row'
                        }`}
                      >
                        <Avatar className="w-8 h-8">
                          <AvatarFallback>
                            {message.sender === 'user' ? (
                              <User className="w-4 h-4" />
                            ) : (
                              <Bot className="w-4 h-4" />
                            )}
                          </AvatarFallback>
                        </Avatar>
                        
                        <div
                          className={`flex flex-col max-w-[80%] ${
                            message.sender === 'user' ? 'items-end' : 'items-start'
                          }`}
                        >
                          {message.sender === 'assistant' && message.agent && (
                            <span className="text-xs text-muted-foreground mb-1">
                              {getAgentName(message.agent)}
                            </span>
                          )}
                          <div
                            className={`rounded-lg px-4 py-2 ${
                              message.sender === 'user'
                                ? 'bg-primary text-primary-foreground'
                                : 'bg-muted'
                            }`}
                          >
                            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                          </div>
                          <span className="text-xs text-muted-foreground mt-1">
                            {mounted ? message.timestamp.toLocaleTimeString([], { 
                              hour: '2-digit', 
                              minute: '2-digit',
                              hour12: true 
                            }) : ''}
                          </span>
                        </div>
                      </div>
                    ))}
                    
                    {isLoading && (
                      <div className="flex gap-3">
                        <Avatar className="w-8 h-8">
                          <AvatarFallback>
                            <Bot className="w-4 h-4" />
                          </AvatarFallback>
                        </Avatar>
                        <div className="bg-muted rounded-lg px-4 py-2">
                          <Loader2 className="w-4 h-4 animate-spin" />
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="p-6 pt-4 border-t">
                  <form onSubmit={handleSubmit} className="flex gap-2">
                  <Input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Type your message here..."
                    disabled={isLoading}
                    className="flex-1"
                  />                    <Button type="submit" disabled={isLoading || !input.trim()}>
                      <Send className="w-4 h-4" />
                    </Button>
                  </form>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
