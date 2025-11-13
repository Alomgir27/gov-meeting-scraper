#!/bin/bash

set -e

echo "=================================="
echo "Meeting Scraper - Setup"
echo "=================================="
echo ""

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "📦 Step 1: Creating virtual environment..."
python -m venv .venv

echo "✓ Virtual environment created"
echo ""

echo "📥 Step 2: Activating virtual environment..."
if [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
else
    source .venv/bin/activate
fi

echo "✓ Virtual environment activated"
echo ""

echo "📦 Step 3: Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "✓ Python dependencies installed"
echo ""

echo "🌐 Step 4: Installing Playwright browser..."
playwright install chromium

echo "✓ Playwright browser installed"
echo ""

mkdir -p outputs
mkdir -p inputs
mkdir -p logs

echo "=================================="
echo "✅ Setup Complete!"
echo "=================================="
echo ""
echo "Ready to scrape! Run:"
echo "  bash run.sh"
echo ""
echo "  2. Run Problem 1 scraper:"
echo "     bash run.sh"
echo ""

