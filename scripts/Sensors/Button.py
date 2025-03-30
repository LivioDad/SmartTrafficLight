from MyMQTT import *
import time
import json
import requests
from gpiozero import Button
import threading
import urllib.request
import os
import signal
import sys


class PedestrianButton:
    def __init__(self, button_info, resource_catalog_file):
        # Retrieve broker info from service catalog
        self.resource_catalog = json.load(open(resource_catalog_file))
        request_string = f'http://{self.resource_catalog["ip_address"]}:{self.resource_catalog["ip_port"]}/broker'
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["name"]
        self.port = rjson["port"]

        # Sensor details
        self.button_info = button_info
        info = json.load(open(self.button_info))
        self.topic = info["servicesDetails"][0]["topic"]
        self.clientID = info["ID"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, None)
        self.button = Button(23)

        self.running = True  # Flag to control thread execution
        self.last_message_time = 0  # Timestamp of last message sent

    def register(self):
        """Periodically register the sensor in the resource catalog."""
        while self.running:
            request_string = f'http://{self.resource_catalog["ip_address"]}:{self.resource_catalog["ip_port"]}/registerResource'
            data = json.load(open(self.button_info))
            try:
                r = requests.put(request_string, json.dumps(data, indent=4))
                print(f'Response: {r.text}')
            except Exception as e:
                print(f'Error during registration: {e}')
            time.sleep(10)

    def start(self):
        """Start MQTT connection."""
        self.client.start()

    def stop(self):
        """Stop MQTT connection and terminate the thread."""
        self.running = False
        self.client.stop()

    def press_callback(self):
        """Callback executed when the button is pressed."""
        current_time = time.time()
        if current_time - self.last_message_time >= 1:  # Avoid spam (1s cooldown)
            msg = {
                "bn": self.clientID,
                "e": {
                    "n": "vul_button",
                    "u": "Boolean",
                    "t": current_time,
                    "v": True
                }
            }
            self.client.myPublish(self.topic, msg)
            print("Published:\n" + json.dumps(msg) + " to topic " + self.topic)
            self.last_message_time = current_time  # Update last press time


def handle_exit(signum, frame):
    """Handle program exit with Ctrl+C."""
    print("\n[INFO] Shutting down...")
    button.stop()
    sys.exit(0)


if __name__ == '__main__':
    # Automatically retrieve the path of JSON config files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    resource_catalog_path = os.path.join(script_dir, "..", "..", "resource_catalog", "resource_catalog_info.json")
    resource_catalog_path = os.path.normpath(resource_catalog_path)
    button_info_path = os.path.join(script_dir, "Button_info.json")
    button_info_path = os.path.normpath(button_info_path)

    button = PedestrianButton(button_info_path, resource_catalog_path)

    # Register Ctrl+C handler
    signal.signal(signal.SIGINT, handle_exit)

    # Start background registration thread
    background_thread = threading.Thread(name='background', target=button.register, daemon=True)
    background_thread.start()

    # Start MQTT connection
    button.start()

    try:
        button.button.when_pressed = button.press_callback
        signal.pause()  # Keep the program running
    finally:
        button.stop()