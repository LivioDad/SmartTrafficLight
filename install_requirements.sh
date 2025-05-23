#!/bin/bash

echo "Checking and installing required Python packages..."

# System dependencies
sudo apt-get update
sudo apt-get install -y python3-pip python3-smbus python3-venv

# Path to virtualenv
VENV="$HOME/Desktop/virtualenv"

# Create if not exists
if [ ! -d "$VENV" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv "$VENV"
fi

# Activate the virtualenv
source "$VENV/bin/activate"

# Install packages
pip install --upgrade pip
pip install \
  adafruit-circuitpython-dht \
  adafruit-blinka \
  gpiozero \
  paho-mqtt \
  requests \
  telepot \
  cherrypy \
  numpy \
  pandas \
  matplotlib \
  scikit-learn \
  joblib

echo "All packages installed inside virtualenv."