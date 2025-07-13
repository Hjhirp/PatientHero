#!/bin/bash

# Test script for Med42-8B deployment
echo "🧪 Testing Med42-8B Deployment"
echo "=============================="

# Set the API URL
API_URL="${1:-https://patienthero-med42.fly.dev}"

echo "Testing API at: $API_URL"
echo ""

# Test 1: Health check
echo "1. Health Check:"
curl -s "$API_URL/health" | jq '.' || echo "Health check failed"
echo ""

# Test 2: List models
echo "2. Available Models:"
curl -s "$API_URL/v1/models" | jq '.data[].id' || echo "Models endpoint failed"
echo ""

# Test 3: Chat completion
echo "3. Chat Completion Test:"
curl -s -X POST "$API_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user", 
        "content": "What is diabetes?"
      }
    ],
    "max_tokens": 150,
    "temperature": 0.7
  }' | jq '.choices[0].message.content' || echo "Chat completion failed"

echo ""
echo "✅ Testing complete!"
