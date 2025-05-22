#!/bin/bash

PID_FILE="script_pids.txt"

echo "Stopping all registered scripts..."
if [ -f "$PID_FILE" ]; then
  while IFS= read -r pid; do
    if kill "$pid" 2>/dev/null; then
      echo "Stopped PID $pid"
    fi
  done < "$PID_FILE"
  rm -f "$PID_FILE"
else
  echo "No PID file found. Skipping registered script shutdown."
fi

echo ""
echo "Cleaning up stray Python processes using GPIO..."
PIDS=$(sudo lsof /dev/gpiochip* 2>/dev/null | awk 'NR>1 {print $2}' | sort -u)
if [ -z "$PIDS" ]; then
  echo "No stray GPIO processes found."
else
  echo "Found PIDs: $PIDS"
  sudo kill -9 $PIDS
  echo "Killed stray GPIO processes."
fi

echo ""
echo "Stopping Docker containers..."
docker compose down

echo "All systems stopped and cleaned."
