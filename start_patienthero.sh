#!/bin/bash

# PatientHero Startup Script
# This script starts both the FastAPI backend and Next.js frontend

set -e  # Exit on any error

echo "🏥 Starting PatientHero Application"
echo "=================================="

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Please run this script from the PatientHero root directory"
    exit 1
fi

# Check if Python dependencies are installed
echo "📦 Checking Python dependencies..."
if ! python3 -c "import fastapi, uvicorn" 2>/dev/null; then
    echo "📦 Installing Python dependencies..."
    pip3 install fastapi uvicorn pydantic python-dotenv
fi

# Check if Node dependencies are installed
echo "📦 Checking Node.js dependencies..."
if [ ! -d "node_modules" ]; then
    echo "📦 Installing Node.js dependencies..."
    npm install
fi

# Start the FastAPI backend in the background
echo "🚀 Starting CrewAI FastAPI backend (port 8000)..."
python3 api_server.py &
BACKEND_PID=$!

# Wait a moment for the backend to start
sleep 3

# Check if backend is running
if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "✅ Backend is running on http://localhost:8000"
else
    echo "⚠️  Backend may not be fully ready yet..."
fi

# Start the Next.js frontend
echo "🚀 Starting Next.js frontend (port 3000)..."
npm run dev &
FRONTEND_PID=$!

# Function to cleanup processes on script exit
cleanup() {
    echo ""
    echo "🛑 Shutting down PatientHero..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    echo "✅ PatientHero stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

echo ""
echo "🎉 PatientHero is starting up!"
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both services"

# Wait for processes
wait
