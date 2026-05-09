#!/bin/bash
# Stop all ArchIQ processes
if [ -f logs/backend.pid ]; then
    kill $(cat logs/backend.pid) 2>/dev/null && echo "✅ Backend stopped"
    rm logs/backend.pid
fi
if [ -f logs/frontend.pid ]; then
    kill $(cat logs/frontend.pid) 2>/dev/null && echo "✅ Frontend stopped"
    rm logs/frontend.pid
fi
echo "ArchIQ stopped."
