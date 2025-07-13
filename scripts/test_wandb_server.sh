#!/bin/bash

# Test DeepSeek R1 W&B Server
echo "🧪 Testing DeepSeek R1 W&B Medical AI Server"
echo "==========================================="

# Set the API URL
API_URL="${1:-http://localhost:8001}"

echo "Testing API at: $API_URL"
echo ""

# Test 1: Health check
echo "1. Health Check:"
curl -s "$API_URL/health" | python3 -m json.tool || echo "Health check failed"
echo ""

# Test 2: List models
echo "2. Available Models:"
curl -s "$API_URL/v1/models" | python3 -m json.tool || echo "Models endpoint failed"
echo ""

# Test 3: Medical chat completion
echo "3. Medical Chat Test:"
curl -s -X POST "$API_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user", 
        "content": "What are the symptoms of diabetes and when should someone see a doctor?"
      }
    ],
    "max_tokens": 300,
    "temperature": 0.7
  }' | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print('Response:')
    print(data['choices'][0]['message']['content'])
    print(f\"\\nTokens used: {data['usage']['total_tokens']}\")
except Exception as e:
    print(f'Error parsing response: {e}')
    sys.stdin.seek(0)
    print(sys.stdin.read())
" || echo "Chat completion failed"

echo ""
echo "✅ Testing complete!"
echo ""
echo "🔗 Available endpoints:"
echo "   - Health: $API_URL/health"
echo "   - Models: $API_URL/v1/models"
echo "   - Chat: $API_URL/v1/chat/completions"
