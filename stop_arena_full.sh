#!/bin/bash
# Stop Arena and External Chatbots

set -e

echo "🛑 Stopping KI-Campus Arena System..."
echo "======================================"
echo ""

# Stop Arena system
echo "📦 Stopping Arena services..."
docker compose -f docker-compose.prod.yml down

# Stop external chatbots
echo "📦 Stopping external chatbots..."
docker compose -f docker-compose.chatbots.yml down

echo ""
echo "✅ All services stopped"
echo ""
echo "🔄 To start again, run: ./start_arena_full.sh"
