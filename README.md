# 🏰 Disneyland Menu Browser

A mobile-friendly web app for browsing all Disneyland restaurant menus and prices in one place.

## Features

### Core Functionality
- 🍔 Browse all food and beverage items across Disneyland
- 🔍 Real-time search across menu items
- 💰 Filter by price range ($0-10, $10-20, $20-30, $30+)
- 📍 Filter by location/land
- 🍽️ Filter by food category
- 📊 Sort by name, price, or restaurant
- ❤️ Save favorites (stored locally)
- 🔄 Manual data refresh button

### Mobile Optimized
- 📱 Responsive design that works great on phones
- 🎯 Touch-friendly interface
- 📋 Card-based layout on small screens
- ⚡ Fast filtering and sorting
- 🏠 Add to home screen for app-like experience

## Quick Start

### Local Development
```bash
# Easy way - using the run script
./run.sh

# Manual way
pip install -r requirements.txt
python disneyland.py --web
```

Then open http://localhost:5000 in your browser.

### Mobile Testing
To test on your phone while developing locally:
1. Find your computer's IP address
2. Make sure your phone is on the same WiFi network
3. Open `http://YOUR_COMPUTER_IP:5000` on your phone

## Deployment

The app is ready to deploy to any of these platforms:

### Easiest Options (Free Tiers Available)
1. **Render** - Just connect your GitHub repo, automatic deployment
2. **Railway** - Simple CLI deployment with `railway up`
3. **PythonAnywhere** - Python-specific hosting, great for Flask

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

## Configuration

The app uses environment variables for configuration. See [.env.example](.env.example) for all available options.

Key settings:
- `CACHE_HOURS` - How long to cache menu data (default: 6 hours)
- `ENABLE_REFRESH_BUTTON` - Show manual refresh button (default: true)
- `ENABLE_FAVORITES` - Enable favorites feature (default: false)

## Project Structure
```
├── disneyland.py          # Main application
├── config.py              # Configuration management
├── templates/
│   ├── index.html         # Main menu browser
│   └── error.html         # Error page
├── disney_responses/      # Cached API responses
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── render.yaml           # Render deployment config
├── DEPLOYMENT.md         # Deployment guide
└── todo.md              # Development progress tracker
```

## Improvements Made

This version includes major improvements over the original:

✅ **Fixed Issues**
- Dynamic date handling (no more hardcoded dates)
- Comprehensive error handling and logging
- Configuration management with environment variables

✅ **Mobile Experience**
- Fully responsive design
- Touch-optimized controls
- Card layout on small screens
- Loading states and animations

✅ **New Features**
- Advanced filtering (category, price range, location)
- Multi-column sorting
- Favorites system
- Data refresh on demand
- Status API endpoint

✅ **Deployment Ready**
- Docker support
- Multiple platform configs (Render, Railway, Heroku)
- Production-ready with proper security
- Comprehensive deployment documentation

## API Status

Check the app's configuration and health:
- `/api/status` - View current configuration and health
- `/api/refresh` - Force refresh of menu data (POST)

## Tips for Best Experience

1. **On iPhone**: Use Safari, tap Share → Add to Home Screen
2. **On Android**: Use Chrome, tap Menu → Add to Home Screen
3. **Performance**: Data is cached for 6 hours by default
4. **Favorites**: Your favorites are saved locally in your browser

## Troubleshooting

- **Slow loading**: First load fetches all restaurant data, subsequent loads use cache
- **No menu items**: Some restaurants might not have online menus
- **Prices show N/A**: Not all items have prices listed online

## License

For personal use only. This app uses publicly available Disney API endpoints.