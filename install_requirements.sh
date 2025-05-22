#!/bin/bash

echo "Checking and installing required Python packages..."

sudo apt-get update
sudo apt-get install -y python3-pip python3-smbus

pip3 install --upgrade pip

pip3 install \
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

echo "All required packages installed."
