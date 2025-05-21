from MyMQTT import *
import time
import json
import requests
from gpiozero import Button
import threading
import os
import signal
import sys

class PedestrianButton:
    def __init__(self, button_info, resource_catalog_file):
        self.resource_catalog = json.load(open(resource_catalog_file))
        request_string = f'http://{self.resource_catalog["ip_address"]}:{self.resource_catalog["ip_port"]}/broker'
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["name"]
        self.port = rjson["port"]

        info = json.load(open(button_info))
        self.topic = info["servicesDetails"][0]["topic"]
        self.topic_direct = info["servicesDetails"][0].get("topic_direct")
        self.clientID = info["ID"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, None)
        self.button = Button(23)
        self.running = True
        self.last_message_time = 0

    def register(self):
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
        self.client.start()

    def stop(self):
        self.running = False
        self.client.stop()

    def press_callback(self):
        current_time = time.time()
        if current_time - self.last_message_time >= 1:
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
            print("Published to manager:\n" + json.dumps(msg))

            if self.topic_direct:
                direct_msg = {
                    "bn": self.clientID,
                    "e": {
                        "n": "led",
                        "u": "detection",
                        "t": current_time,
                        "v": "vulnerable_pedestrian",
                        "source": "direct"
                    }
                }
                self.client.myPublish(self.topic_direct, direct_msg)
                print("Published directly:\n" + json.dumps(direct_msg))

            self.last_message_time = current_time

def handle_exit(signum, frame):
    print("\n[INFO] Shutting down...")
    button.stop()
    sys.exit(0)

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    #resource_catalog_path = os.path.normpath(os.path.join(script_dir, "..", "resource_catalog", "resource_catalog_info.json"))
    resource_catalog_path = os.path.join(script_dir, 'resource_catalog_info.json')
    button_info_path = os.path.normpath(os.path.join(script_dir, "Button_info.json"))

    button = PedestrianButton(button_info_path, resource_catalog_path)
    button.button_info = button_info_path

    signal.signal(signal.SIGINT, handle_exit)

    threading.Thread(target=button.register, daemon=True).start()
    button.start()

    try:
        button.button.when_pressed = button.press_callback
        signal.pause()
    finally:
        button.stop()