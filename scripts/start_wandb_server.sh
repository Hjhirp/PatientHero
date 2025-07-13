#!/bin/bash

# Start DeepSeek R1 W&B Server
echo "🚀 Starting DeepSeek R1 Medical AI Server on W&B"
echo "================================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run ./setup_wandb.sh first."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create it from .env.example"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check if W&B API key is set
if [ -z "$WANDB_API_KEY" ] || [ "$WANDB_API_KEY" = "your_wandb_api_key_here" ]; then
    echo "⚠️  Warning: WANDB_API_KEY not configured. Server will run in demo mode."
    echo "   Get your API key from: https://wandb.ai/settings"
fi

echo "🔧 Configuration:"
echo "   - Port: ${PORT:-8001}"
echo "   - W&B Entity: ${WANDB_ENTITY:-'not set'}"
echo "   - W&B Project: ${WANDB_PROJECT:-'patienthero-deepseek'}"
echo "   - W&B API Key: ${WANDB_API_KEY:0:8}..." if [ -n "$WANDB_API_KEY" ]
echo ""

# Start the server
echo "🏥 Starting PatientHero DeepSeek R1 server..."
python3 wandb_deepseek_service.py
