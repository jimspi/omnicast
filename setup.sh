#!/bin/bash
# OmniCast Setup Script

echo "======================================"
echo "  OmniCast Setup Script"
echo "======================================"
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version || { echo "Python 3 is required but not installed."; exit 1; }

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check for FFmpeg
echo ""
echo "Checking for FFmpeg..."
if command -v ffmpeg &> /dev/null; then
    echo "FFmpeg found: $(ffmpeg -version 2>&1 | head -n1)"
else
    echo "WARNING: FFmpeg not found!"
    echo "Please install FFmpeg for video processing features."
    echo "  Ubuntu/Debian: sudo apt install ffmpeg"
    echo "  macOS: brew install ffmpeg"
    echo "  Windows: Download from https://ffmpeg.org/download.html"
fi

# Create .env file if not exists
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env and add your OPENAI_API_KEY"
fi

echo ""
echo "======================================"
echo "  Setup Complete!"
echo "======================================"
echo ""
echo "To start the server:"
echo "  1. Activate the virtual environment: source venv/bin/activate"
echo "  2. Set your OpenAI API key in .env file"
echo "  3. Run: python run.py"
echo ""
echo "Then open http://localhost:8000 in your browser"
echo ""
