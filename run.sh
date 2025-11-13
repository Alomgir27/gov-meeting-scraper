#!/bin/bash

set -e

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

if [ "$1" == "problem2" ] || [ "$1" == "2" ]; then
    echo "=================================="
    echo "Meeting Scraper - Problem 2"
    echo "=================================="
    echo ""
    echo "🚀 Starting Problem 2 URL resolver..."
    echo "   🔗 URLs: 11 unique domains (12 total with duplicate)"
    echo "   ✅ Verification: yt-dlp --simulate + HTTP checks"
    echo "   🎯 Platforms: Swagit, IBM Video, Granicus, SharePoint, etc."
    echo ""
    
    python scraper.py resolve-urls \
        --input inputs/problem2_input.json \
        --output outputs/problem2_output.json
    
    echo ""
    echo "=================================="
    echo "✅ URL Resolution Complete!"
    echo "=================================="
    echo ""
    echo "📄 Output: outputs/problem2_output.json"
    echo "📊 Logs: logs/"
    echo ""
else
    echo "=================================="
    echo "Meeting Scraper - Problem 1"
    echo "=================================="
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
fi

