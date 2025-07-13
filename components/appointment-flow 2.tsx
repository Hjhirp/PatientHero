'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { CalendarIcon, MapPinIcon, PhoneIcon, ClockIcon, HeartIcon } from 'lucide-react';

interface AppointmentData {
  hospital_name: string;
  website: string;
  institution_type: string;
  accepts_user_insurance: string;
  processing_status: string;
  appointment_availability: {
    available_slots: Array<{
      time: string;
      source: string;
      booking_available: boolean;
      slot_type: string;
    }>;
    total_slots_found: number;
    next_available: string | null;
    booking_method: string;
  };
  processing_error?: string;
}

interface ComfortGuidance {
  round: number;
  message: string;
  agent: string;
  next_guidance_available: boolean;
}

interface AppointmentFlowProps {
  sessionId: string;
  onFlowComplete?: () => void;
}

export default function AppointmentFlow({ sessionId, onFlowComplete }: AppointmentFlowProps) {
  const [isProcessing, setIsProcessing] = useState(false);
  const [appointments, setAppointments] = useState<AppointmentData[]>([]);
  const [comfortGuidance, setComfortGuidance] = useState<ComfortGuidance | null>(null);
  const [currentStep, setCurrentStep] = useState<'processing' | 'results' | 'comfort' | 'journey'>('processing');
  const [error, setError] = useState<string | null>(null);
  const [comfortRound, setComfortRound] = useState(1);

  const processCompleteFlow = async () => {
    setIsProcessing(true);
    setError(null);
    
    try {
      // Ensure we have a valid session ID
      const validSessionId = sessionId || `frontend-${Date.now()}`;
      console.log('Starting complete medical flow with session:', validSessionId);
      
      const response = await fetch(`http://localhost:8000/api/complete-flow/${validSessionId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Complete flow response:', data);

      // Set appointments data
      if (data.appointments?.institutions_with_appointments) {
        setAppointments(data.appointments.institutions_with_appointments);
      }

      // Set comfort guidance
      if (data.comfort_guidance) {
        setComfortGuidance(data.comfort_guidance);
      }

      setCurrentStep('results');
      
    } catch (err) {
      console.error('Error in complete flow:', err);
      const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
      console.error('Detailed error:', {
        error: err,
        sessionId: sessionId,
        validSessionId: sessionId || `frontend-${Date.now()}`
      });
      setError(`Failed to process appointment flow: ${errorMessage}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const getNextComfortGuidance = async () => {
    if (comfortRound >= 2) return;

    try {
      const response = await fetch(`http://localhost:8000/api/comfort-guidance/${sessionId}?round_number=${comfortRound + 1}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setComfortGuidance({
        round: data.round,
        message: data.guidance,
        agent: data.agent,
        next_guidance_available: data.next_round !== null
      });
      setComfortRound(data.round);
      
    } catch (err) {
      console.error('Error getting comfort guidance:', err);
      setError('Failed to get comfort guidance');
    }
  };

  useEffect(() => {
    // Always process the flow, even if sessionId is empty (we'll generate one)
    processCompleteFlow();
  }, []);

  const renderProcessingStep = () => (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ClockIcon className="h-5 w-5 animate-spin" />
          Processing Your Medical Information
        </CardTitle>
        <CardDescription>
          We're finding available appointments and preparing comfort guidance for your journey
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
        </div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <div className="animate-pulse">🔍</div>
          <span>Scanning medical institutions for appointment availability...</span>
        </div>
      </CardContent>
    </Card>
  );

  const renderAppointmentResults = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CalendarIcon className="h-5 w-5" />
            Available Appointments Found
          </CardTitle>
          <CardDescription>
            {appointments.length} medical institutions with available appointment slots
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4">
            {appointments.map((appointment, index) => (
              <Card key={index} className="border-l-4 border-l-green-500">
                <CardHeader className="pb-3">
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="text-lg">{appointment.hospital_name}</CardTitle>
                      <Badge variant="outline" className="mt-1">
                        {appointment.institution_type}
                      </Badge>
                    </div>
                    <Badge variant={appointment.appointment_availability.total_slots_found > 0 ? "default" : "secondary"}>
                      {appointment.appointment_availability.total_slots_found} slots
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm">
                      <MapPinIcon className="h-4 w-4" />
                      <a 
                        href={appointment.website} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        Visit Website
                      </a>
                    </div>
                    
                    {appointment.appointment_availability.next_available && (
                      <div className="flex items-center gap-2 text-sm font-medium text-green-600">
                        <ClockIcon className="h-4 w-4" />
                        Next Available: {appointment.appointment_availability.next_available}
                      </div>
                    )}
                    
                    <div className="flex items-center gap-2 text-sm">
                      <PhoneIcon className="h-4 w-4" />
                      Insurance: {appointment.accepts_user_insurance === 'unknown' ? 'Call to verify' : appointment.accepts_user_insurance}
                    </div>
                  </div>
                  
                  {appointment.appointment_availability.available_slots.length > 0 && (
                    <div className="mt-3">
                      <p className="text-sm font-medium mb-2">Available Times:</p>
                      <div className="flex flex-wrap gap-2">
                        {appointment.appointment_availability.available_slots.slice(0, 3).map((slot, slotIndex) => (
                          <Badge key={slotIndex} variant="outline">
                            {slot.time}
                          </Badge>
                        ))}
                        {appointment.appointment_availability.available_slots.length > 3 && (
                          <Badge variant="outline">
                            +{appointment.appointment_availability.available_slots.length - 3} more
                          </Badge>
                        )}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
          
          <div className="flex gap-4 mt-6">
            <Button 
              onClick={() => setCurrentStep('comfort')}
              className="flex-1"
            >
              Continue to Comfort Guidance
            </Button>
            <Button 
              variant="outline" 
              onClick={() => window.location.reload()}
            >
              Refresh Results
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );

  const renderComfortGuidance = () => (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <HeartIcon className="h-5 w-5 text-red-500" />
          Comfort & Journey Guidance
          <Badge variant="outline">Round {comfortGuidance?.round || 1}</Badge>
        </CardTitle>
        <CardDescription>
          Supportive guidance for your journey to the hospital
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {comfortGuidance && (
          <div className="bg-blue-50 p-4 rounded-lg border-l-4 border-l-blue-500">
            <p className="text-sm font-medium text-blue-900 mb-2">
              From {comfortGuidance.agent}:
            </p>
            <p className="text-blue-800 leading-relaxed">
              {comfortGuidance.message}
            </p>
          </div>
        )}
        
        <div className="flex gap-3">
          {comfortGuidance?.next_guidance_available && comfortRound < 2 && (
            <Button 
              onClick={getNextComfortGuidance}
              variant="outline"
            >
              Get Next Guidance (Round {comfortRound + 1})
            </Button>
          )}
          
          <Button 
            onClick={() => {
              setCurrentStep('journey');
              onFlowComplete?.();
            }}
          >
            I'm Ready to Go
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  const renderJourneyComplete = () => (
    <Card className="w-full max-w-2xl mx-auto text-center">
      <CardHeader>
        <CardTitle className="flex items-center justify-center gap-2 text-green-600">
          <HeartIcon className="h-6 w-6" />
          Journey Support Complete
        </CardTitle>
        <CardDescription>
          You're all set! Safe travels to your appointment.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="bg-green-50 p-4 rounded-lg">
            <p className="text-green-800 font-medium">✅ Appointments Found & Reviewed</p>
            <p className="text-green-800 font-medium">✅ Comfort Guidance Provided</p>
            <p className="text-green-800 font-medium">✅ Ready for Hospital Visit</p>
          </div>
          
          <Button 
            onClick={() => window.location.href = '/'}
            className="w-full"
          >
            Return to Main Chat
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  if (error) {
    return (
      <Card className="w-full max-w-2xl mx-auto">
        <CardHeader>
          <CardTitle className="text-red-600">Error</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-red-600">{error}</p>
          <Button 
            onClick={() => {
              setError(null);
              processCompleteFlow();
            }}
            className="mt-4"
          >
            Try Again
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="container mx-auto p-4 space-y-6">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-blue-600 mb-2">
          PatientHero Complete Medical Flow
        </h1>
        <p className="text-blue-500">
          Finding appointments and providing journey support
        </p>
      </div>

      {currentStep === 'processing' && isProcessing && renderProcessingStep()}
      {currentStep === 'results' && renderAppointmentResults()}
      {currentStep === 'comfort' && renderComfortGuidance()}
      {currentStep === 'journey' && renderJourneyComplete()}
    </div>
  );
}
