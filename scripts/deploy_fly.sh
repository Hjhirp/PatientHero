#!/bin/bash

# PatientHero Med42-8B Deployment Script
# This script helps deploy the Med42-8B model to Fly.io

set -e

echo "🚀 PatientHero Med42-8B Deployment"
echo "=================================="

# Check if flyctl is installed
if ! command -v flyctl &> /dev/null; then
    echo "❌ flyctl is not installed. Please install it first:"
    echo "   curl -L https://fly.io/install.sh | sh"
    exit 1
fi

# Check if logged into Fly.io
if ! flyctl auth whoami &> /dev/null; then
    echo "🔐 Please log into Fly.io first:"
    echo "   flyctl auth login"
    exit 1
fi

# Create app if it doesn't exist
echo "📱 Creating Fly.io app (if not exists)..."
flyctl apps create patienthero-med42 --org personal || echo "App may already exist"

# Create volume for model cache
echo "💾 Creating volume for model cache..."
flyctl volumes create model_cache --region ord --size 50 --app patienthero-med42 || echo "Volume may already exist"

# Set secrets (optional - for Hugging Face authentication)
echo "🔑 Setting up environment..."
read -p "Do you have a Hugging Face token? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter your Hugging Face token: " -s HF_TOKEN
    echo
    flyctl secrets set HF_TOKEN="$HF_TOKEN" --app patienthero-med42
fi

# Deploy the application
echo "🚢 Deploying Med42-8B to Fly.io..."
flyctl deploy --app patienthero-med42

echo "✅ Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "1. Wait for the model to download (this may take 5-10 minutes on first deployment)"
echo "2. Check status: flyctl status --app patienthero-med42"
echo "3. View logs: flyctl logs --app patienthero-med42"
echo "4. Your API will be available at: https://patienthero-med42.fly.dev"
echo ""
echo "🧪 Test your deployment:"
echo "curl https://patienthero-med42.fly.dev/health"
echo ""
echo "💰 Estimated costs:"
echo "- A10 GPU: ~$1.50/hour when running"
echo "- Storage: ~$5/month for 50GB"
echo "- Auto-scales to zero when idle"
