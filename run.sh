#!/bin/bash

# Start script for Disneyland Menu app

echo "🏰 Starting Disneyland Menu App..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -q -r requirements.txt

# Set development environment
export FLASK_ENV=development
export FLASK_DEBUG=true

# Run the app
echo "🚀 Starting web server..."
echo "📱 Open http://localhost:5000 in your browser"
echo "📱 For mobile testing, use your computer's IP address"
echo ""

python disneyland.py --web