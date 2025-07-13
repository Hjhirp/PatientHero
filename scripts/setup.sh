#!/bin/bash

# PatientHero Quick Setup Script
echo "🏥 PatientHero - AI Healthcare Assistant Setup"
echo "=============================================="

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version 18+ is required. Current version: $(node -v)"
    exit 1
fi

echo "✅ Node.js $(node -v) detected"

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Create environment file if it doesn't exist
if [ ! -f ".env.local" ]; then
    echo "🔧 Creating .env.local file..."
    cp .env.example .env.local
    echo "⚠️  Please update .env.local with your configuration"
else
    echo "✅ .env.local already exists"
fi

# Run type check
echo "🔍 Running type check..."
npm run type-check

if [ $? -eq 0 ]; then
    echo "✅ Type check passed!"
else
    echo "❌ Type check failed. Please fix the errors and try again."
    exit 1
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Deploy Med42-8B model to Fly.io:"
echo "   cd fly-llm-server && ./deploy.sh"
echo "2. Update .env.local with your Fly.io URL"
echo "3. Start development server: npm run dev"
echo "4. Open http://localhost:3000"
echo ""
echo "📚 Documentation:"
echo "- Deployment guide: fly-llm-server/DEPLOYMENT.md"
echo "- README: README.md"
echo ""
echo "🧪 Test your deployment:"
echo "   cd fly-llm-server && ./test-deployment.sh"
echo ""
echo "🚀 Happy coding!"
