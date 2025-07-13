#!/bin/bash

# Quick Component Tests for PatientHero
# Test individual parts of the system

echo "🔍 PatientHero Component Tests"
echo "==============================="

# Test 1: Backend API Test
echo ""
echo "🧪 Test 1: Backend API (requires backend running)"
echo "-------------------------------------------------"
echo "Testing if FastAPI backend is responding..."

if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "✅ Backend API is running"
    echo "Response:"
    curl -s http://localhost:8000/ | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/
else
    echo "❌ Backend API not responding on http://localhost:8000"
    echo "Start backend with: python3 api_server.py"
fi

# Test 2: Frontend Test
echo ""
echo "🧪 Test 2: Frontend (requires frontend running)"
echo "-----------------------------------------------"
echo "Testing if Next.js frontend is responding..."

if curl -s http://localhost:3000/ > /dev/null 2>&1; then
    echo "✅ Frontend is running on http://localhost:3000"
else
    echo "❌ Frontend not responding on http://localhost:3000"
    echo "Start frontend with: npm run dev"
fi

# Test 3: CrewAI Direct Test
echo ""
echo "🧪 Test 3: CrewAI Agents (direct Python test)"
echo "---------------------------------------------"
echo "Testing CrewAI agents directly..."

cd crewai_agents || { echo "❌ crewai_agents directory not found"; exit 1; }

# Check if main.py exists and can be imported
python3 -c "
import sys
import os
sys.path.append(os.getcwd())

try:
    from main import PatientHeroCrewAI
    print('✅ PatientHeroCrewAI can be imported')
    
    # Test basic initialization
    try:
        patient_hero = PatientHeroCrewAI()
        print('✅ PatientHeroCrewAI can be initialized')
        print(f'✅ Session ID: {patient_hero.patient_data.session_id}')
    except Exception as e:
        print(f'❌ Initialization failed: {e}')
        
except ImportError as e:
    print(f'❌ Import failed: {e}')
    print('Check if all dependencies are installed')
except Exception as e:
    print(f'❌ Error: {e}')
" 2>/dev/null || echo "❌ CrewAI test failed - check Python environment"

cd ..

# Test 4: ExaHelper Test
echo ""
echo "🧪 Test 4: ExaHelper (requires EXA_API_KEY)"
echo "-------------------------------------------"
echo "Testing ExaHelper integration..."

cd crewai_agents || exit 1

python3 -c "
import sys
import os
sys.path.append(os.getcwd())

try:
    from exa_helper import ExaHelper
    print('✅ ExaHelper can be imported')
    
    # Check if API key is available
    from dotenv import load_dotenv
    load_dotenv('../.env')
    
    exa_api_key = os.getenv('EXA_API_KEY')
    if exa_api_key and 'your_' not in exa_api_key:
        print('✅ EXA_API_KEY is configured')
        
        # Test ExaHelper initialization
        try:
            exa_helper = ExaHelper()
            print('✅ ExaHelper initialized successfully')
        except Exception as e:
            print(f'❌ ExaHelper initialization failed: {e}')
    else:
        print('⚠️  EXA_API_KEY not configured in .env')
        
except ImportError as e:
    print(f'❌ ExaHelper import failed: {e}')
except Exception as e:
    print(f'❌ Error: {e}')
" 2>/dev/null || echo "❌ ExaHelper test failed"

cd ..

# Test 5: API Integration Test
echo ""
echo "🧪 Test 5: API Integration (requires both services running)"
echo "---------------------------------------------------------"
echo "Testing full API integration..."

if curl -s http://localhost:8000/ > /dev/null 2>&1 && curl -s http://localhost:3000/ > /dev/null 2>&1; then
    echo "Testing chat API endpoint..."
    
    RESPONSE=$(curl -s -X POST http://localhost:3000/api/chat \
        -H "Content-Type: application/json" \
        -d '{"message": "Hello", "sessionId": null}')
    
    if [ $? -eq 0 ]; then
        echo "✅ Chat API responded"
        echo "Response preview:"
        echo "$RESPONSE" | python3 -m json.tool 2>/dev/null | head -10 || echo "$RESPONSE" | head -3
    else
        echo "❌ Chat API failed"
    fi
else
    echo "❌ Both frontend and backend must be running for this test"
    echo "Start with: ./start_patienthero.sh"
fi

echo ""
echo "📊 Test Summary"
echo "==============="
echo "Run individual tests:"
echo "- Backend only: python3 api_server.py"
echo "- Frontend only: npm run dev"
echo "- Full system: ./start_patienthero.sh"
echo ""
echo "Manual testing URLs:"
echo "- Frontend: http://localhost:3000"
echo "- Backend API docs: http://localhost:8000/docs"
echo "- Backend status: http://localhost:8000/"
