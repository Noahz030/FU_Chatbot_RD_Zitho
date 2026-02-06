#!/bin/bash
# Start Arena with External Chatbots
# This script starts both external chatbot versions and the Arena system

set -e  # Exit on error

echo "🚀 Starting KI-Campus Arena with External Chatbots"
echo "=================================================="
echo ""

# Check if Docker is running
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Check if Azure CLI is authenticated
if ! az account show > /dev/null 2>&1; then
    echo "⚠️  Azure CLI not authenticated. Running az login..."
    az login --tenant "c6ff58bc-993e-4bdb-8d10-6013e2cd361f"
fi

echo "✅ Prerequisites OK"
echo ""

# Step 1: Start external chatbots
echo "📦 Step 1: Starting External Chatbots..."
echo "  - Original: http://localhost:9001"
echo "  - Improved: http://localhost:9002"
echo ""

docker compose -f docker/docker-compose.chatbots.yml up -d chatbot-original chatbot-improved

echo "⏳ Waiting for chatbots to be healthy..."
sleep 10

# Health check
if curl -f http://localhost:9001/health > /dev/null 2>&1; then
    echo "✅ Original chatbot healthy"
else
    echo "❌ Original chatbot not responding"
    echo "   Check logs: docker logs chatbot-original"
fi

if curl -f http://localhost:9002/health > /dev/null 2>&1; then
    echo "✅ Improved chatbot healthy"
else
    echo "❌ Improved chatbot not responding"
    echo "   Check logs: docker logs chatbot-improved"
fi

echo ""

# Step 2: Start Arena system
echo "📦 Step 2: Starting Arena System..."
echo "  - Arena API:  http://localhost:8001"
echo "  - Arena UI:   http://localhost:8002"
echo ""

docker compose -f docker/docker-compose.prod.yml up -d arena-api arena-ui

echo "⏳ Waiting for Arena to be healthy..."
sleep 5

# Health check
if curl -f http://localhost:8001/health > /dev/null 2>&1; then
    echo "✅ Arena API healthy"
else
    echo "❌ Arena API not responding"
    echo "   Check logs: docker logs fu-arena-api"
fi

if curl -f http://localhost:8002/ > /dev/null 2>&1; then
    echo "✅ Arena UI accessible"
else
    echo "❌ Arena UI not responding"
    echo "   Check logs: docker logs fu-arena-ui"
fi

echo ""
echo "=================================================="
echo "🎉 Arena System Started!"
echo ""
echo "📊 Available Services:"
echo "  - Chatbot Original:  http://localhost:9001/health"
echo "  - Chatbot Improved:  http://localhost:9002/health"
echo "  - Arena API:         http://localhost:8001/health"
echo "  - Arena Voting UI:   http://localhost:8002/"
echo "  - Results Dashboard: http://localhost:8002/results"
echo "  - User Votes:        http://localhost:8002/user-votes"
echo ""
echo "🔍 Check logs:"
echo "  docker logs chatbot-original"
echo "  docker logs chatbot-improved"
echo "  docker logs fu-arena-api"
echo "  docker logs fu-arena-ui"
echo ""
echo "🛑 Stop all:"
echo "  ./stop_arena_full.sh"
echo "=================================================="
