# PatientHero Deployment Guide

## Overview

PatientHero now supports two AI deployment options with automatic fallback:

1. **Primary**: Med42-8B on Fly.io (when available)
2. **Fallback**: DeepSeek R1 on Weights & Biases (W&B)

The system automatically tries the primary service first, and falls back to the secondary if needed.

## Quick Start Options

### Option 1: W&B DeepSeek R1 (Recommended for now)

Since Fly.io has blocked your account, start with the W&B deployment:

```bash
# 1. Set up W&B DeepSeek R1 server
cd wandb-server
./setup_wandb.sh

# 2. Configure W&B credentials
# Edit wandb-server/.env with your W&B API key
# Get key from: https://wandb.ai/settings

# 3. Start the W&B server
./start_server.sh

# 4. In another terminal, start the frontend
cd ..
npm run dev
```

### Option 2: Fly.io Med42-8B (When account is restored)

```bash
# 1. Deploy to Fly.io (when account is unblocked)
cd fly-llm-server
fly launch

# 2. Start the frontend
cd ..
npm run dev
```

## Detailed Setup

### W&B DeepSeek R1 Setup

1. **Get W&B API Key**:
   - Visit https://wandb.ai/settings
   - Copy your API key

2. **Configure the server**:
   ```bash
   cd wandb-server
   cp .env.example .env
   # Edit .env and set:
   # WANDB_API_KEY=your_actual_api_key
   # WANDB_ENTITY=your_wandb_username
   ```

3. **Install and start**:
   ```bash
   ./setup_wandb.sh
   ./start_server.sh
   ```

4. **Test the deployment**:
   ```bash
   ./test_wandb_server.sh
   ```

### Frontend Configuration

The frontend automatically uses both services:

```bash
# Primary service (Fly.io)
NEXT_PUBLIC_AI_API_URL=https://patienthero-med42.fly.dev

# Fallback service (W&B)
NEXT_PUBLIC_WANDB_API_URL=http://localhost:8001
```

## Architecture

```
Frontend (Next.js)
     ↓
AI Service Layer (Auto-fallback)
     ↓
┌─────────────────┬─────────────────┐
│ Primary         │ Fallback        │
│ Fly.io Med42-8B │ W&B DeepSeek R1 │
└─────────────────┴─────────────────┘
```

## Service Comparison

| Feature | Fly.io Med42-8B | W&B DeepSeek R1 |
|---------|-----------------|-----------------|
| **Cost** | $50-150/month | Free tier available |
| **Setup** | 15 minutes | 10 minutes |
| **Performance** | Very Fast (A10 GPU) | Fast (cloud) |
| **Availability** | 99.9% uptime | Depends on W&B |
| **Medical Focus** | Specialized | General + medical prompts |

## Troubleshooting

### W&B Server Issues

1. **Import errors**: Run `./setup_wandb.sh` again
2. **API key errors**: Check your W&B API key in `.env`
3. **Connection issues**: Ensure port 8001 is available

### Frontend Issues

1. **No AI response**: Check if either service is running
2. **Slow responses**: Normal for first requests (model loading)
3. **Errors**: Check browser console for details

## Testing

### Test W&B Service
```bash
cd wandb-server
./test_wandb_server.sh
```

### Test Fly.io Service (when available)
```bash
cd fly-llm-server
./test-deployment.sh
```

### Test Frontend Integration
1. Start the appropriate backend service
2. Start frontend: `npm run dev`
3. Open http://localhost:3000
4. Send a test medical question
5. Verify AI responses

## Production Deployment

### W&B Production
- Deploy the W&B server to a cloud platform (Heroku, Railway, etc.)
- Update `NEXT_PUBLIC_WANDB_API_URL` to your production URL

### Fly.io Production
- Complete Fly.io account verification
- Deploy using `fly launch`
- Update `NEXT_PUBLIC_AI_API_URL` to your Fly.io URL

## Next Steps

1. **Start with W&B**: Get the system running with DeepSeek R1
2. **Test thoroughly**: Ensure medical AI responses are appropriate
3. **Monitor performance**: Check response times and quality
4. **Add Fly.io later**: When account access is restored
5. **Customize prompts**: Adapt for your specific medical use cases

The dual-service architecture ensures your medical AI chatbot remains available even if one service has issues!
