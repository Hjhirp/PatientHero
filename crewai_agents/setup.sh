#!/bin/bash

echo "🏥 Setting up PatientHero CrewAI Agents"
echo "======================================="

# Check if conda is available
if command -v conda &> /dev/null; then
    echo "Conda detected. Creating conda environment: patienthero-crewai..."
    
    # Option 1: Create from environment.yml (preferred)
    if [ -f "environment.yml" ]; then
        echo "Using environment.yml for setup..."
        conda env create -f environment.yml
    else
        # Option 2: Create environment and install with pip
        echo "Creating conda environment and installing with pip..."
        conda create -n patienthero-crewai python=3.11 -y
        
        # Activate conda environment
        echo "Activating conda environment..."
        source $(conda info --base)/etc/profile.d/conda.sh
        conda activate patienthero-crewai
        
        # Install requirements
        echo "Installing Python packages with pip..."
        pip install -r requirements.txt
    fi
    
    echo "✅ Conda environment 'patienthero-crewai' created successfully!"
    echo ""
    echo "To activate the environment, run:"
    echo "conda activate patienthero-crewai"
    
else
    echo "⚠️  Conda not found. Creating Python virtual environment instead..."
    
    # Fallback to venv
    python -m venv patienthero-crewai-venv
    source patienthero-crewai-venv/bin/activate
    pip install -r requirements.txt
    
    echo "✅ Virtual environment 'patienthero-crewai-venv' created!"
    echo ""
    echo "To activate the environment, run:"
    echo "source patienthero-crewai-venv/bin/activate"
fi

# Copy environment template
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your API keys before running the system"
fi

echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Activate the environment (see command above)"
echo "3. Run the system: python main.py"
