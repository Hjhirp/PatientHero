#!/bin/bash

# PatientHero Environment Setup Script
# Sets up both Python and Node.js environments

set -e  # Exit on any error

echo "🏥 Setting up PatientHero Development Environment"
echo "==============================================="

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Please run this script from the PatientHero root directory"
    exit 1
fi

# Check Python version
echo "🐍 Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python $PYTHON_VERSION found"

# Check Node.js version
echo "📦 Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18 or higher."
    exit 1
fi

NODE_VERSION=$(node -v)
echo "✅ Node.js $NODE_VERSION found"

# Create Python virtual environment
echo "🔧 Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
echo "📦 Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r backend_requirements.txt
echo "✅ Python dependencies installed"

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
npm install
echo "✅ Node.js dependencies installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "🔑 Creating .env file..."
    cat > .env << EOF
# PatientHero Environment Variables
# Copy this file and add your actual API keys

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here

# Exa API
EXA_API_KEY=your_exa_api_key_here

# Wandb (optional)
WANDB_API_KEY=your_wandb_api_key_here
WANDB_PROJECT=patienthero-crewai
WANDB_ENTITY=your_wandb_entity_here

# Backend Configuration
CREWAI_BACKEND_URL=http://localhost:8000
PORT=8000
HOST=0.0.0.0

# Data paths
EXTRACTED_DATA_OUTPUT_PATH=./extracted_patient_data.json
EOF
    echo "✅ .env file created"
    echo "⚠️  Please edit .env and add your actual API keys!"
else
    echo "✅ .env file already exists"
fi

# Create a simple test script
cat > test_setup.py << EOF
#!/usr/bin/env python3
"""Test script to verify PatientHero setup"""

import sys
import os

def test_imports():
    """Test if all required packages can be imported"""
    required_packages = [
        'fastapi',
        'uvicorn', 
        'pydantic',
        'crewai',
        'google.generativeai',
        'exa_py',
        'wandb',
        'weave',
        'dotenv'
    ]
    
    print("Testing Python package imports...")
    failed_imports = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError as e:
            print(f"❌ {package}: {e}")
            failed_imports.append(package)
    
    if failed_imports:
        print(f"\n❌ Failed to import: {', '.join(failed_imports)}")
        print("Please run: pip install -r backend_requirements.txt")
        return False
    else:
        print("\n✅ All Python packages imported successfully!")
        return True

def test_env_file():
    """Test if .env file exists and has required keys"""
    if not os.path.exists('.env'):
        print("❌ .env file not found")
        return False
    
    print("\n🔑 Checking .env file...")
    with open('.env', 'r') as f:
        env_content = f.read()
    
    required_keys = ['GEMINI_API_KEY', 'EXA_API_KEY']
    missing_keys = []
    
    for key in required_keys:
        if f"{key}=your_" in env_content or key not in env_content:
            missing_keys.append(key)
            print(f"⚠️  {key} needs to be set")
        else:
            print(f"✅ {key} is configured")
    
    if missing_keys:
        print(f"\n⚠️  Please set these API keys in .env: {', '.join(missing_keys)}")
        return False
    else:
        print("\n✅ All required API keys are configured!")
        return True

if __name__ == "__main__":
    print("🏥 PatientHero Setup Test")
    print("========================")
    
    imports_ok = test_imports()
    env_ok = test_env_file()
    
    if imports_ok and env_ok:
        print("\n🎉 PatientHero setup is complete!")
        print("Run './start_patienthero.sh' to start the application")
    else:
        print("\n❌ Setup incomplete. Please fix the issues above.")
        sys.exit(1)
EOF

chmod +x test_setup.py

echo ""
echo "🎉 PatientHero environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your API keys"
echo "2. Run './test_setup.py' to verify setup"
echo "3. Run './start_patienthero.sh' to start the application"
echo ""
echo "API Keys needed:"
echo "- GEMINI_API_KEY: Get from https://ai.google.dev/"
echo "- EXA_API_KEY: Get from https://exa.ai/"
echo "- WANDB_API_KEY: Get from https://wandb.ai/ (optional)"
