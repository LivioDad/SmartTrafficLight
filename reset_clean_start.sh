#!/bin/bash

echo "Stopping running Docker containers..."
docker compose down

echo "Removing Docker images related to the project..."
docker images --format '{{.Repository}}:{{.Tag}} {{.ID}}' | grep 'smarttrafficlight' | awk '{print $2}' | xargs -r docker rmi -f

echo "Removing unused Docker volumes and networks..."
docker volume prune -f
docker network prune -f

echo "Cleaning logs, PID file, and __pycache__ folders..."
rm -rf logs
rm -f script_pids.txt
find . -type d -name '__pycache__' -exec rm -rf {} +

echo "Project has been reset. You can now run ./start_system.sh to simulate a fresh start."
