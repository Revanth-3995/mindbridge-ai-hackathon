#!/bin/bash

# Mind Bridge AI ML Service Startup Script

echo "🚀 Starting Mind Bridge AI ML Service"
echo "====================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed or not in PATH"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check if service is already running
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "⚠️  Service is already running on port 8001"
    echo "   Stopping existing service..."
    pkill -f "uvicorn main:app"
    sleep 2
fi

# Start the service
echo "🎯 Starting ML service on port 8001..."
echo "   Health check: http://localhost:8001/health"
echo "   API docs: http://localhost:8001/docs"
echo "   Press Ctrl+C to stop"
echo ""

uvicorn main:app --reload --port 8001 --host 0.0.0.0
