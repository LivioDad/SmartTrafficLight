#!/bin/bash

echo "Stopping all running scripts..."

# Kill all scripts launched from script_pids.txt
if [ -f script_pids.txt ]; then
    while read pid; do
        kill -9 "$pid" 2>/dev/null
    done < script_pids.txt
    > script_pids.txt
fi

# Additional process cleanup (manual pkill fallback)
echo "Killing known Python GPIO processes..."
pkill -f DHT22.py
pkill -f PIR.py
pkill -f Semaphore_
pkill -f infraction_sensor.py

# GPIO reset steps
echo "Resetting GPIO state..."

# Attempt soft GPIO chip reset
sudo lgpiochipctl --chip 0 --reset

# Kill pigpiod if running
sudo killall pigpiod 2>/dev/null

# Unbind GPIO chip (may fail on some systems, ignore errors)
echo none | sudo tee /sys/class/gpio/gpiochip0/subsystem/unbind > /dev/null
sleep 1
echo 0 | sudo tee /sys/class/gpio/export > /dev/null

echo "All scripts stopped and GPIO cleaned up."