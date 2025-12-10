#!/bin/bash
# Start-Script für OpenWebUI Arena Mode mit Voting System
# Startet alle benötigten Services mit einem Befehl

set -e

echo "🚀 OpenWebUI Arena Mode Startup"
echo "================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd /Users/browse/FU_Chatbot_RD_Zitho

# Check Azure Login
echo -e "${YELLOW}1. Prüfe Azure Login...${NC}"
if ! az account show > /dev/null 2>&1; then
    echo -e "${YELLOW}   Azure Session abgelaufen. Login erforderlich...${NC}"
    az login --tenant "c6ff58bc-993e-4bdb-8d10-6013e2cd361f"
else
    echo -e "${GREEN}✓ Azure Login aktiv${NC}"
fi

# Start API
echo -e "\n${YELLOW}2. Starte LLM-API (Port 8001)...${NC}"
export KEY_VAULT_NAME="kicwa-keyvault-lab"
/Users/browse/.pyenv/versions/3.11.7/bin/python -m uvicorn src.openwebui.openwebui_api_llm:app --host 0.0.0.0 --port 8001 > /tmp/llm_api.log 2>&1 &
API_PID=$!
sleep 3
echo -e "${GREEN}✓ API gestartet (PID: $API_PID)${NC}"

# Start OpenWebUI
echo -e "${YELLOW}3. Starte OpenWebUI Container (Port 3001)...${NC}"
docker rm -f openwebui 2>/dev/null || true
docker run -d \
  --name openwebui \
  -p 3001:8080 \
  -v open-webui:/app/backend/data \
  --add-host=host.docker.internal:host-gateway \
  ghcr.io/open-webui/open-webui:main > /dev/null 2>&1
echo -e "${GREEN}✓ OpenWebUI startet...${NC}"

# Start Voting UI
echo -e "${YELLOW}4. Starte Voting UI (Port 8002)...${NC}"
/Users/browse/.pyenv/versions/3.11.7/bin/python -m uvicorn src.openwebui.voting_ui:app --host 0.0.0.0 --port 8002 > /tmp/voting_ui.log 2>&1 &
VOTING_PID=$!
sleep 2
echo -e "${GREEN}✓ Voting UI gestartet (PID: $VOTING_PID)${NC}"

# Verify Services
echo -e "\n${YELLOW}5. Verifiziere Services...${NC}"
sleep 3

# Check API
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API antwortet${NC}"
else
    echo -e "${YELLOW}⚠ API antwortet noch nicht (startet sich automatisch)${NC}"
fi

# Check OpenWebUI
if curl -s http://localhost:3001 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ OpenWebUI erreichbar${NC}"
else
    echo -e "${YELLOW}⚠ OpenWebUI startet noch...${NC}"
fi

# Check Voting UI
if curl -s http://localhost:8002 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Voting UI erreichbar${NC}"
else
    echo -e "${YELLOW}⚠ Voting UI startet noch...${NC}"
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Alle Services starten!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "🌐 URLs:"
echo "  • OpenWebUI Chat:    http://localhost:3001"
echo "  • Voting Dashboard:  http://localhost:8002"
echo "  • API Docs:          http://localhost:8001/docs"
echo ""
echo "📖 Dokumentation: src/openwebui/SETUP.md"
echo ""
echo "🛑 Zum Stoppen: pkill -f 'uvicorn'; docker stop openwebui"
echo ""
