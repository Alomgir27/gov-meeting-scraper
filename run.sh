#!/bin/bash

set -e

echo "=================================="
echo "Meeting Scraper - Problem 1"
echo "=================================="
echo ""

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run: bash setup.sh"
    exit 1
fi

echo "🔧 Activating virtual environment..."
if [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
else
    source .venv/bin/activate
fi

mkdir -p outputs inputs logs

echo "✓ Environment ready"
echo ""

echo "🚀 Starting Problem 1 scraper..."
echo "   📅 Date range: 2024-11-20 to 2025-11-26"
echo "   🌐 Domains: 6 URLs from assignment"
echo "   ⚙️  Features: Retry logic, bot avoidance, rate limiting"
echo ""

python scraper.py scrape-meetings \
    --input inputs/problem1_all_domains.json \
    --output outputs/problem1_complete_output.json

echo ""
echo "=================================="
echo "✅ Scraping Complete!"
echo "=================================="
echo ""
echo "📄 Output: outputs/problem1_complete_output.json"
echo "📊 Logs: logs/"
echo ""

