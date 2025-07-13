#!/bin/bash

# PatientHero Testing Guide
# Step-by-step commands to test the full integration

echo "🏥 PatientHero Integration Testing Guide"
echo "========================================"
echo ""

echo "📋 Prerequisites Check:"
echo "----------------------"

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Please run this from the PatientHero root directory"
    exit 1
fi

echo "✅ In PatientHero directory"

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo "✅ Python $PYTHON_VERSION found"
else
    echo "❌ Python 3 not found - please install Python 3.8+"
    exit 1
fi

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node -v)
    echo "✅ Node.js $NODE_VERSION found"
else
    echo "❌ Node.js not found - please install Node.js 18+"
    exit 1
fi

echo ""
echo "🔧 STEP 1: Environment Setup"
echo "----------------------------"
echo "Run: ./setup_environment.sh"
echo ""
read -p "Press Enter to run environment setup..."

if [ -x "./setup_environment.sh" ]; then
    ./setup_environment.sh
else
    echo "❌ setup_environment.sh not found or not executable"
    echo "Run: chmod +x setup_environment.sh"
    exit 1
fi

echo ""
echo "🔑 STEP 2: Configure API Keys"
echo "-----------------------------"
echo "Edit the .env file with your actual API keys:"
echo ""
echo "Required keys:"
echo "- GEMINI_API_KEY (get from https://ai.google.dev/)"
echo "- EXA_API_KEY (get from https://exa.ai/)"
echo ""
echo "Current .env file:"
cat .env | grep -E "(GEMINI_API_KEY|EXA_API_KEY)" || echo "No .env file found"
echo ""
read -p "Have you added your API keys to .env? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Please edit .env file first:"
    echo "nano .env"
    exit 1
fi

echo ""
echo "🧪 STEP 3: Test Python Setup"
echo "----------------------------"
echo "Run: ./test_setup.py"
echo ""
read -p "Press Enter to test Python setup..."

if [ -x "./test_setup.py" ]; then
    ./test_setup.py
    if [ $? -ne 0 ]; then
        echo "❌ Python setup test failed"
        exit 1
    fi
else
    echo "❌ test_setup.py not found or not executable"
    echo "Run: chmod +x test_setup.py"
    exit 1
fi

echo ""
echo "🚀 STEP 4: Start the Application"
echo "--------------------------------"
echo "Run: ./start_patienthero.sh"
echo ""
echo "This will start both:"
echo "- FastAPI backend on http://localhost:8000"
echo "- Next.js frontend on http://localhost:3000"
echo ""
read -p "Press Enter to start the application..."

if [ -x "./start_patienthero.sh" ]; then
    echo "Starting PatientHero... (Press Ctrl+C to stop)"
    ./start_patienthero.sh
else
    echo "❌ start_patienthero.sh not found or not executable"
    echo "Run: chmod +x start_patienthero.sh"
    exit 1
fi
