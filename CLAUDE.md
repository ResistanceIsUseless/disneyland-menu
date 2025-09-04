# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a mobile-friendly Flask web application for browsing Disneyland restaurant menus and prices. The app fetches data from Disney's API, caches it locally, and provides a responsive interface with filtering, search, and favorites functionality.

## Development Commands

### Local Development
```bash
# Quick start using the run script (recommended)
./run.sh

# Manual setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python disneyland.py --web
```

### Command Line Usage
```bash
# Web server mode
python disneyland.py --web

# CLI mode to fetch and display menu data
python disneyland.py

# Enable debug output
python disneyland.py --debug

# Specify a date for API queries
python disneyland.py --date 2025-01-15
```

### Deployment
The app includes configuration for multiple deployment platforms:
- **Render**: Uses `render.yaml` configuration
- **Docker**: Uses `Dockerfile` with Gunicorn
- **Railway/Heroku**: Uses `Procfile`

See `DEPLOYMENT.md` for detailed deployment instructions.

## Architecture

### Core Components

**Main Application** (`disneyland.py:1-556`)
- `DisneylandMenuFetcher` class handles Disney API interactions with retry logic and caching
- `create_app()` factory function creates the Flask application
- Supports both CLI and web modes

**Configuration Management** (`config.py:1-114`)
- Environment-based configuration with development/production classes
- All settings configurable via environment variables
- Built-in validation for configuration values

**API Flow**
1. Authentication: Gets auth token from Disney's authz endpoint
2. Restaurant Discovery: Fetches list of all restaurants
3. Menu Fetching: For each restaurant, fetches detailed menu data
4. Data Processing: Flattens menu items with restaurant metadata

### Key Features

**Caching System**
- Responses cached in `disney_responses/` directory for configurable hours
- GitHub Actions automatically fetch fresh data hourly and commit to repo
- App prioritizes pre-committed cache files in read-only environments (like Render)
- Graceful fallback to API calls if no cache files exist
- Docker-aware caching with optional persistent volumes for local development
- Configurable automatic cleanup (disabled by default for containers)

**Mobile-First Design**
- Responsive templates in `templates/` directory
- Touch-friendly filtering and sorting
- Card-based layout for small screens
- Loading overlay shows during initial data fetch

**Enhanced Filtering**
- Hide N/A price button to filter out items without pricing
- Quick filter buttons for specific items (Pretzels, Churros)
- Advanced filtering by location, price range, and category

**Configuration Architecture**
- All paths, timeouts, and feature flags configurable via environment variables
- Separate development and production configurations
- Configuration validation with error reporting

## Development Notes

### Environment Variables
Key configuration options (see `config.py` for full list):
- `CACHE_HOURS`: Cache duration (default: 6 hours)
- `CACHE_CLEANUP_DAYS`: Days to keep old cache files (default: 7)
- `CACHE_AUTO_CLEANUP`: Enable automatic cleanup on startup (default: false for containers)
- `FLASK_ENV`: Set to 'production' for production config
- `ENABLE_REFRESH_BUTTON`: Show manual refresh button (default: true)
- `ENABLE_FAVORITES`: Enable favorites feature (default: false)

### Docker Deployment
The app is Docker-ready with intelligent caching:
- `docker-compose.yml` provided for easy deployment with persistent cache
- Cache volumes can be mounted for persistence across container restarts
- Auto-cleanup disabled by default to work better in container environments
- Use `CACHE_AUTO_CLEANUP=true` in managed environments like Kubernetes

### Automated Data Fetching
GitHub Actions workflow (`.github/workflows/fetch-disney-data.yml`):
- Runs hourly to fetch fresh Disney API data
- Commits cache files directly to the repository
- Ensures Render deployments start with pre-cached data for instant loading
- Can be manually triggered via GitHub Actions tab

### API Endpoints
- `/api/status`: View current configuration and health
- `/api/refresh`: Force refresh of menu data (POST)
- `/api/cleanup-cache`: Manually trigger cache cleanup (POST)

### API Integration
The app authenticates with Disney's API using a multi-step process that requires specific headers and maintains session state. All API interactions go through the `DisneylandMenuFetcher` class which handles retries, logging, and response caching.

### Data Structure
Menu items are flattened from nested restaurant data into a single array with restaurant metadata attached to each item, enabling efficient filtering and sorting in the frontend.