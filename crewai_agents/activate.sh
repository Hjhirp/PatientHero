#!/bin/bash

# Quick activation script for PatientHero CrewAI environment

echo "🏥 Activating PatientHero CrewAI Environment"
echo "==========================================="

# Check if conda environment exists
if conda env list | grep -q "patienthero-crewai"; then
    echo "✅ Conda environment 'patienthero-crewai' found"
    echo "Activating conda environment..."
    conda activate patienthero-crewai
    echo "Environment activated! You can now run:"
    echo "  python main.py              # Start the interactive system"
    echo "  python test_extraction.py   # Run extraction tests"
    echo "  conda deactivate            # Exit environment"
elif [ -d "patienthero-crewai-venv" ]; then
    echo "✅ Virtual environment 'patienthero-crewai-venv' found"
    echo "Activating virtual environment..."
    source patienthero-crewai-venv/bin/activate
    echo "Environment activated! You can now run:"
    echo "  python main.py              # Start the interactive system"
    echo "  python test_extraction.py   # Run extraction tests"
    echo "  deactivate                  # Exit environment"
else
    echo "❌ No PatientHero environment found!"
    echo "Please run setup first:"
    echo "  chmod +x setup.sh && ./setup.sh"
fi
