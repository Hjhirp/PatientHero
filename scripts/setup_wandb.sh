#!/bin/bash

# DeepSeek R1 on W&B Setup Script for PatientHero
echo "🧠 Setting up DeepSeek R1 with Weights & Biases for PatientHero"
echo "=============================================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python $PYTHON_VERSION detected"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "🔧 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please update .env with your W&B API key and configuration"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🎉 DeepSeek R1 W&B setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Update .env with your W&B API key:"
echo "   - Get API key from: https://wandb.ai/settings"
echo "   - Set WANDB_API_KEY in .env file"
echo "   - Set WANDB_ENTITY to your W&B username"
echo "2. Start the server: ./start_server.sh"
echo "3. Test the server: ./test_wandb_server.sh"
echo ""
echo "📚 Documentation:"
echo "- W&B Documentation: https://docs.wandb.ai/"
echo "- DeepSeek R1 Model: https://huggingface.co/deepseek-ai/deepseek-r1"
echo ""
echo "🚀 Ready to deploy medical AI with DeepSeek R1!"
