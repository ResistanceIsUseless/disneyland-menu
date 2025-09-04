# Deployment Guide for Disneyland Menu App

## Quick Deployment Options

### Option 1: Render (Recommended - Free Tier Available)

1. Fork or push this repository to GitHub
2. Sign up for a free account at [render.com](https://render.com)
3. Click "New +" and select "Web Service"
4. Connect your GitHub repository
5. Render will automatically detect the `render.yaml` configuration
6. Click "Create Web Service"
7. Your app will be deployed at `https://your-app-name.onrender.com`

**Note on Render caching:**
- Render Web Services have ephemeral filesystems - cache resets on restarts/deployments
- The app will still optimize API calls within each session
- First load after restart will be slower, subsequent loads will be fast
- Consider shorter `CACHE_HOURS` (4) for Render to balance freshness vs API load

### Option 2: Railway

1. Install Railway CLI: `npm i -g @railway/cli`
2. Run `railway login`
3. Run `railway init` in the project directory
4. Run `railway up`
5. Run `railway open` to view your deployed app

### Option 3: Docker (Any Cloud Provider)

Build and run locally:
```bash
docker build -t disneyland-menu .
docker run -p 8080:8080 disneyland-menu
```

**With persistent cache (recommended for production):**
```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Or with Docker run
docker run -p 8080:8080 -v disneyland_cache:/app/disney_responses disneyland-menu
```

**Environment variables for Docker:**
- `CACHE_AUTO_CLEANUP=true` - Enable automatic cache cleanup in managed environments
- `CACHE_CLEANUP_DAYS=3` - More aggressive cleanup for containers (default: 7)
- `CACHE_HOURS=12` - Longer cache duration for production (default: 6)

Deploy to cloud:
- **Google Cloud Run**: `gcloud run deploy --source .` (cache will reset on each deployment)
- **Azure Container Instances**: Push to Azure Container Registry, then deploy
- **AWS ECS**: Push to ECR, create task definition, deploy to ECS (consider EFS for persistent cache)

**Note on caching in containers:**
- Without persistent volumes, cache resets on container restart
- Use volumes or managed storage for cache persistence in production
- The app intelligently avoids redundant API calls within the same session

### Option 4: PythonAnywhere

1. Sign up at [pythonanywhere.com](https://www.pythonanywhere.com)
2. Upload files via the Files tab
3. Create a new web app (Flask, Python 3.11)
4. Configure WSGI file:
```python
import sys
path = '/home/yourusername/disneyland-menu'
if path not in sys.path:
    sys.path.append(path)
from disneyland import create_app
application = create_app()
```

### Option 5: Vercel (Serverless)

1. Install Vercel CLI: `npm i -g vercel`
2. Create `vercel.json`:
```json
{
  "builds": [
    {
      "src": "disneyland.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "disneyland.py"
    }
  ]
}
```
3. Run `vercel` and follow prompts

## Environment Variables

Set these environment variables in your hosting platform:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SECRET_KEY` | Flask secret key | auto-generated | Yes (production) |
| `FLASK_ENV` | Environment mode | development | No |
| `PORT` | Server port | 5000 | No |
| `CACHE_HOURS` | Cache duration | 6 | No |
| `ENABLE_REFRESH_BUTTON` | Show refresh button | true | No |
| `ENABLE_FAVORITES` | Enable favorites feature | false | No |
| `LOG_LEVEL` | Logging level | INFO | No |

## Post-Deployment

1. Test the app on your mobile device
2. Add to home screen for app-like experience:
   - iOS: Safari > Share > Add to Home Screen
   - Android: Chrome > Menu > Add to Home Screen
3. Monitor logs for any errors
4. Consider setting up a custom domain

## Performance Tips

- Set `CACHE_HOURS=12` or higher in production
- Enable CDN if available on your platform
- Consider adding Redis for better caching (optional)

## Troubleshooting

### App loads slowly
- Increase `CACHE_HOURS`
- Check if free tier has cold starts

### API errors
- Disney API might have rate limits
- Check logs for specific error messages
- Verify date format is correct

### Mobile display issues
- Clear browser cache
- Try different browsers
- Check viewport meta tag is present

## Support

For issues, check:
1. Application logs in your hosting platform
2. `/api/status` endpoint for configuration info
3. Browser console for JavaScript errors