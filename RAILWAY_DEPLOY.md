# 🚀 Railway Deployment Guide

## Quick Deploy

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/new?template=https://github.com/YOUR_REPO)

## Prerequisites

- GitHub account
- Railway account (free tier available)
- API keys for:
  - Cohere (embeddings)
  - Qdrant (vector database)
  - OpenAI/OpenRouter (LLM)
  - Neon (PostgreSQL, optional for logging)

---

## Step-by-Step Deployment

### 1. Prepare Your Repository

Ensure your code is pushed to GitHub:

```bash
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

### 2. Connect to Railway

1. Go to [Railway](https://railway.app/)
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your repository: `Humanoid-Robotics-AI-textbook/backend`

### 3. Configure Environment Variables

In Railway dashboard, go to **Variables** tab and add:

```bash
# Required - Cohere (Embeddings)
COHERE_API_KEY=your_cohere_api_key

# Required - Qdrant (Vector DB)
QDRANT_URL=https://your-cluster.qdrant.tech
QDRANT_API_KEY=your_qdrant_api_key

# Required - LLM Provider
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=meta-llama/llama-3-8b-instruct

# Optional - PostgreSQL (Logging)
NEON_DATABASE_URL=postgresql://user:pass@host.db.neon.tech/dbname?sslmode=require

# Optional - OpenAI (Fallback)
OPENAI_API_KEY=your_openai_key
```

### 4. Configure Build Settings

In Railway dashboard, go to **Settings**:

- **Build Command**: Leave empty (uses Dockerfile)
- **Start Command**: Leave empty (uses Procfile/CMD)
- **Root Directory**: `backend`

### 5. Deploy

Railway will automatically:
- Detect the `Dockerfile` or `Procfile`
- Install dependencies from `requirements.txt`
- Start the FastAPI server

---

## Testing Your Deployment

### Health Check

```bash
curl https://your-app.railway.app/health
```

Expected response:
```json
{"status": "healthy", "timestamp": 1234567890}
```

### Chat Endpoint

```bash
curl -X POST https://your-app.railway.app/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is humanoid robotics?"}'
```

---

## Troubleshooting

### Build Fails

**Issue**: Missing dependencies
```bash
# Check requirements.txt has all packages
pip install -r requirements.txt
```

**Issue**: Python version mismatch
```bash
# Railway uses Python 3.11 from Dockerfile
# Ensure your code is compatible
```

### Runtime Errors

**Issue**: Missing environment variables
- Check Railway dashboard → Variables
- Ensure all required keys are set

**Issue**: API key errors
- Verify API keys are correct
- Check API quotas/limits

**Issue**: Database connection fails
- Verify Neon database URL format
- Ensure SSL mode is set: `?sslmode=require`

### Performance Issues

**Issue**: Slow responses
- Enable caching in your RAG agent
- Consider upgrading Railway plan for more resources

---

## Monitoring

### Railway Dashboard

- **Logs**: Real-time application logs
- **Metrics**: CPU, memory, network usage
- **Deployments**: Deployment history and rollbacks

### Health Endpoints

- `GET /` - API info
- `GET /health` - Health check
- `GET /api/v1/health` - API health
- `GET /api/v1/stats` - Cache statistics

---

## Cost Optimization

### Free Tier Limits

- Railway: $5 credit/month (500 hours)
- Qdrant: Free tier available
- Cohere: Free tier with rate limits

### Tips

1. Use caching to reduce API calls
2. Enable pre-computed answers for common questions
3. Monitor usage in Railway dashboard
4. Set up spending alerts

---

## CI/CD (Optional)

### Auto-deploy on Push

Railway automatically deploys on push to `main` branch.

### Manual Trigger

```bash
# Force redeploy
railway up
```

---

## Rollback

If deployment fails:

1. Go to Railway dashboard → Deployments
2. Click on previous successful deployment
3. Click **"Rollback"**

---

## Support

- [Railway Docs](https://docs.railway.app/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Qdrant Docs](https://qdrant.tech/documentation/)
