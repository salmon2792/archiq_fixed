#!/bin/bash
# ArchIQ Local Setup — run this once to get everything running
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}"
echo "  █████╗ ██████╗  ██████╗██╗  ██╗    ██╗ ██████╗ "
echo " ██╔══██╗██╔══██╗██╔════╝██║  ██║    ██║██╔═══██╗"
echo " ███████║██████╔╝██║     ███████║    ██║██║   ██║"
echo " ██╔══██║██╔══██╗██║     ██╔══██║    ██║██║▄▄ ██║"
echo " ██║  ██║██║  ██║╚██████╗██║  ██║    ██║╚██████╔╝"
echo " ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝    ╚═╝ ╚══▀▀═╝ "
echo -e "${NC}"
echo "Architecture-Aware Career Intelligence Platform"
echo "================================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install from https://python.org"
    exit 1
fi

# Check if Docker is available (optional)
USE_DOCKER=false
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo -e "${BLUE}Docker found. Use Docker? (y/n)${NC}"
    read -r USE_DOCKER_ANS
    if [[ "$USE_DOCKER_ANS" == "y" ]]; then
        USE_DOCKER=true
    fi
fi

if [ "$USE_DOCKER" = true ]; then
    echo -e "${BLUE}🐳 Starting with Docker Compose...${NC}"
    docker-compose up --build -d
    echo ""
    echo -e "${GREEN}✅ ArchIQ is running!${NC}"
    echo "  🌐 Frontend: http://localhost:3000"
    echo "  🔧 Backend API: http://localhost:8000"
    echo "  📚 API Docs: http://localhost:8000/docs"
    exit 0
fi

# Python setup
echo -e "${BLUE}📦 Setting up Python backend...${NC}"
cd backend

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

source venv/bin/activate
pip install -r requirements.txt -q
echo "✅ Dependencies installed"

# Start backend
echo -e "${BLUE}🚀 Starting backend on port 8000...${NC}"
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > ../logs/backend.pid
echo "✅ Backend started (PID: $BACKEND_PID)"

cd ..

# Start frontend
echo -e "${BLUE}🌐 Starting frontend on port 3000...${NC}"
mkdir -p logs

if command -v python3 &> /dev/null; then
    cd frontend
    nohup python3 -m http.server 3000 > ../logs/frontend.log 2>&1 &
    FE_PID=$!
    echo $FE_PID > ../logs/frontend.pid
    cd ..
    echo "✅ Frontend started (PID: $FE_PID)"
fi

# Wait for backend
echo -e "${YELLOW}⏳ Waiting for backend to initialize...${NC}"
sleep 4

# Check health
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend healthy${NC}"
else
    echo -e "${YELLOW}⚠️  Backend still starting — check logs/backend.log${NC}"
fi

echo ""
echo -e "${GREEN}🎉 ArchIQ is running!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🌐 Open in browser: http://localhost:3000"
echo "  🔧 API: http://localhost:8000"
echo "  📚 API Docs: http://localhost:8000/docs"
echo "  📋 Logs: ./logs/"
echo ""
echo "  To install as mobile app:"
echo "  → Open http://localhost:3000 on your phone"
echo "  → Tap 'Add to Home Screen' in your browser"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Open browser
if command -v open &> /dev/null; then
    sleep 2 && open http://localhost:3000
elif command -v xdg-open &> /dev/null; then
    sleep 2 && xdg-open http://localhost:3000
fi
