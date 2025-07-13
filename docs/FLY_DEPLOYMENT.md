# Med42-8B Deployment Guide

This guide will help you deploy the `m42-health/Llama3-Med42-8B` model on Fly.io for use with your PatientHero chatbot.

## Why Med42-8B?

- **Cost Effective**: ~70% less expensive than 70B version
- **Fast Performance**: Quick response times with A10 GPU
- **Medical Focused**: Specialized for healthcare conversations
- **Production Ready**: Reliable performance with good quality

## Prerequisites

1. **Fly.io Account**: Sign up at [fly.io](https://fly.io)
2. **Fly CLI**: Install flyctl
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```
3. **Docker**: Ensure Docker is installed and running
4. **Hugging Face Account**: Optional, for accessing gated models

## Step 1: Prepare for Deployment

1. **Login to Fly.io**:
   ```bash
   flyctl auth login
   ```

2. **Navigate to the LLM server directory**:
   ```bash
   cd fly-llm-server
   ```

3. **Review Configuration**:
   - Check `fly.toml` for app settings
   - Current specs: A10 GPU, 32GB RAM (optimized for 8B model)
   - Region: ord (Chicago) - adjust if needed

## Step 2: Deploy the Model

### Option A: Quick Deploy (Automated)
```bash
./deploy.sh
```

### Option B: Manual Deploy
1. **Create the app**:
   ```bash
   flyctl apps create patienthero-med42
   ```

2. **Create volume for model cache**:
   ```bash
   flyctl volumes create model_cache --region ord --size 50
   ```

3. **Set Hugging Face token** (if needed):
   ```bash
   flyctl secrets set HF_TOKEN=your_hf_token_here
   ```

4. **Deploy**:
   ```bash
   flyctl deploy
   ```

## Step 3: Monitor Deployment

1. **Check deployment status**:
   ```bash
   flyctl status --app patienthero-med42
   ```

2. **View logs** (important for first deployment):
   ```bash
   flyctl logs --app patienthero-med42
   ```

3. **Health check**:
   ```bash
   curl https://patienthero-med42.fly.dev/health
   ```

## Step 4: Configure Frontend

1. **Update environment variables**:
   Create `.env.local` in your frontend directory:
   ```bash
   NEXT_PUBLIC_AI_API_URL=https://patienthero-med42.fly.dev
   ```

2. **Test integration**:
   Your frontend should now connect to the deployed model automatically.

## Important Notes

### First Deployment
- **Download Time**: The model (~16GB) will download on first request
- **Expect 5-10 minutes** for initial setup
- Monitor logs during this process
- The health check will fail until download completes

### Cost Considerations
- **GPU Instance**: A10 costs ~$1.50/hour when running
- **Auto-scaling**: Configured to scale to zero when idle
- **Volume**: 50GB storage ~$5/month
- **Total estimated cost**: $20-80/month depending on usage

### Performance
- **Cold starts**: 1-2 minutes when scaling from zero
- **Warm requests**: 1-5 seconds response time
- **Concurrent requests**: 2-4 recommended per GPU
- **Quality**: Very good for most medical conversations

### Troubleshooting

1. **Model download fails**:
   ```bash
   flyctl ssh console --app patienthero-med42
   # Check disk space and logs
   df -h
   tail -f /var/log/app.log
   ```

2. **Out of memory**:
   - 8B model requires ~12GB VRAM minimum
   - A10 GPU has 24GB VRAM (plenty of headroom)

3. **Slow responses**:
   - Check if multiple requests are queued
   - Consider limiting max_tokens to 256-512

4. **Connection issues**:
   ```bash
   # Test connectivity
   flyctl ssh console --app patienthero-med42
   curl localhost:8000/health
   ```

## Performance Comparison

| Model | Size | VRAM | Response Time | Quality | Cost/Hour |
|-------|------|------|---------------|---------|-----------|
| **Med42-8B** | 16GB | 12GB | 1-3s | Very Good | $1.50 |
| Med42-70B | 140GB | 40GB | 3-8s | Excellent | $3.20 |

## Scaling Options

1. **Horizontal Scaling**:
   ```bash
   flyctl scale count 2 --app patienthero-med42
   ```

2. **Different Regions**:
   ```bash
   flyctl regions add lax syd --app patienthero-med42
   ```

3. **Upgrade GPU** (if needed):
   Update `fly.toml`:
   ```toml
   [vm]
   gpu_kind = "l40s"  # More powerful GPU
   memory = "48gb"
   ```

## Monitoring

1. **Metrics Dashboard**:
   ```bash
   flyctl dashboard --app patienthero-med42
   ```

2. **Resource Usage**:
   ```bash
   flyctl metrics --app patienthero-med42
   ```

3. **Custom Monitoring**: Add logging and metrics as needed

## Alternative Configurations

### Ultra-Low Cost Setup
```toml
# For minimal usage
[vm]
gpu_kind = "a10"
memory = "16gb"  # Minimum for 8B model
```

### High-Performance Setup
```toml
# For high traffic
[vm]
gpu_kind = "l40s"
memory = "48gb"
```

## Support

- **Fly.io Docs**: https://fly.io/docs/
- **Med42 Model**: https://huggingface.co/m42-health/Llama3-Med42-8B
- **Issues**: Check the model card and community discussions

---

🚀 **Your Med42-8B model should now be running on Fly.io and integrated with PatientHero!**

**Total setup time**: ~10 minutes  
**Monthly cost**: ~$20-80 (depending on usage)  
**Response quality**: Very good for healthcare conversations
