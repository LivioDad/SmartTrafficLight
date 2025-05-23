#!/bin/bash
./install_requirements.sh

LOG_DIR="logs"
PID_FILE="script_pids.txt"

mkdir -p "$LOG_DIR"
> "$PID_FILE"

# Docker image check & build (first-time setup)
if ! docker compose images | grep -q 'resource_catalog'; then
  echo "Docker images not found. Running docker compose build..."
  docker compose build
else
  echo "Docker images already built. Skipping build step."
fi

echo "Starting Docker containers..."
docker compose up -d

echo "Waiting 10 seconds for services to initialize..."
sleep 10

echo "Launching main Python scripts..."

python3 Sensors/DHT22.py > "$LOG_DIR/DHT22.log" 2>&1 &
echo $! >> "$PID_FILE"

python3 Sensors/Button.py > "$LOG_DIR/Button.log" 2>&1 &
echo $! >> "$PID_FILE"
sleep 1

python3 Sensors/PIR.py > "$LOG_DIR/PIR.log" 2>&1 &
echo $! >> "$PID_FILE"
sleep 1

python3 violation_detection/infraction_sensor.py > "$LOG_DIR/infraction_sensor.log" 2>&1 &
echo $! >> "$PID_FILE"

python3 Semaphores/Semaphore_1.py > "$LOG_DIR/Semaphore_1.log" 2>&1 &
echo $! >> "$PID_FILE"

python3 Semaphores/Semaphore_2.py > "$LOG_DIR/Semaphore_2.log" 2>&1 &
echo $! >> "$PID_FILE"

echo "Main scripts started. Logs saved in $LOG_DIR/"
echo "To stop all running scripts: ./stop_system.sh"

# Interactive menu for optional scripts
while true; do
  echo ""
  echo "Optional scripts menu:"
  echo "1. Start emergency_sim.py"
  echo "2. Start ice_risk_sim.py"
  echo "3. Add new semaphore"
  echo "4. Exit"
  read -p "Enter your choice [1-4]: " choice

  case $choice in
    1)
      echo "Launching emergency_sim.py... (Press Ctrl+C to return to menu)"
      trap "" SIGINT
      ( trap "echo -e '\\nReturning to menu...'; exit" SIGINT; python3 LedManager/emergency_sim.py )
      trap - SIGINT
      ;;

    2)
      echo "Launching ice_risk_sim.py... (Press Ctrl+C to return to menu)"
      trap "" SIGINT
      ( trap "echo -e '\\nReturning to menu...'; exit" SIGINT; python3 services/ice_risk_sim.py )
      trap - SIGINT
      ;;

    3)
      echo "Launching Add_semaphore.py... (Press Ctrl+C to return to menu)"
      trap "" SIGINT
      ( trap "echo -e '\\nReturning to menu...'; exit" SIGINT; python3 Semaphores/Add_semaphore.py )
      trap - SIGINT
      ;;

    4)
      echo "Exiting optional script menu."
      break
      ;;

    *)
      echo "Invalid choice. Please enter 1, 2, 3 or 4."
      ;;
  esac
done