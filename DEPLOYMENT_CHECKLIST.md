# Railway Deployment Checklist ✅

## Pre-Deployment Checklist

### Code & Configuration
- [x] ✅ `requirements.txt` - All dependencies listed
- [x] ✅ `Procfile` - Start command defined
- [x] ✅ `railway.json` - Railway configuration
- [x] ✅ `Dockerfile.railway` - Docker build instructions
- [x] ✅ `.env.example` - Environment variables template
- [x] ✅ `RAILWAY_DEPLOY.md` - Deployment guide

### API Keys Required
- [ ] ⬜ Cohere API Key (embeddings)
- [ ] ⬜ Qdrant URL & API Key (vector database)
- [ ] ⬜ OpenRouter/OpenAI API Key (LLM)
- [ ] ⬜ Neon Database URL (optional, for logging)

---

## Deployment Steps

### 1️⃣ Push to GitHub
```bash
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

### 2️⃣ Create Railway Project
1. Go to https://railway.app/
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose `Humanoid-Robotics-AI-textbook/backend`

### 3️⃣ Configure Environment Variables

In Railway dashboard → **Variables** tab:

```bash
# Required
COHERE_API_KEY=your_cohere_key_here
QDRANT_URL=https://your-cluster.qdrant.tech
QDRANT_API_KEY=your_qdrant_key_here
OPENROUTER_API_KEY=your_openrouter_key_here

# Optional
NEON_DATABASE_URL=postgresql://...
OPENAI_API_KEY=your_openai_key_here
```

### 4️⃣ Deploy
Railway will automatically:
- ✅ Detect `Dockerfile.railway`
- ✅ Build the image
- ✅ Start the server

---

## Post-Deployment Verification

### Health Check
```bash
curl https://your-app.railway.app/health
# Expected: {"status": "healthy", "timestamp": ...}
```

### Root Endpoint
```bash
curl https://your-app.railway.app/
# Expected: {"message": "Humanoid Robotics RAG API is running"}
```

### Chat Endpoint Test
```bash
curl -X POST https://your-app.railway.app/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is humanoid robotics?"}'
```

---

## Troubleshooting

### Build Fails
| Issue | Solution |
|-------|----------|
| Missing dependencies | Check `requirements.txt` |
| Python version | Ensure 3.11+ compatibility |
| Docker build error | Check `Dockerfile.railway` syntax |

### Runtime Errors
| Issue | Solution |
|-------|----------|
| Missing env vars | Set in Railway dashboard |
| API key errors | Verify keys are correct |
| Database connection | Check Neon URL format |
| Port binding error | Use `$PORT` env var |

### Performance Issues
- Enable caching in RAG agent
- Check API rate limits
- Monitor Railway metrics

---

## Monitoring

### Railway Dashboard
- **Logs**: Real-time application logs
- **Metrics**: CPU, memory, network
- **Deployments**: History & rollbacks

### Health Endpoints
- `GET /` - API info
- `GET /health` - Health check
- `GET /api/v1/health` - API health
- `GET /api/v1/stats` - Cache stats

---

## Cost Management

### Free Tier Limits
- Railway: $5 credit/month
- Qdrant: Free tier available
- Cohere: Rate-limited free tier

### Optimization Tips
1. ✅ Use response caching
2. ✅ Enable pre-computed answers
3. ✅ Monitor usage in dashboard
4. ✅ Set spending alerts

---

## Support Resources

- [Railway Documentation](https://docs.railway.app/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Cohere Documentation](https://docs.cohere.com/)

---

## Deployment Status

| Component | Status |
|-----------|--------|
| Code Ready | ✅ |
| Dockerfile | ✅ |
| Procfile | ✅ |
| Railway Config | ✅ |
| Environment Template | ✅ |
| Deployment Guide | ✅ |
| API Keys | ⬜ User Action Required |
| GitHub Push | ⬜ User Action Required |
| Railway Deploy | ⬜ User Action Required |

---

**Next Step**: Push your code to GitHub and follow the deployment steps in [RAILWAY_DEPLOY.md](RAILWAY_DEPLOY.md)
