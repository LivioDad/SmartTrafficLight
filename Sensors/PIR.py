from MyMQTT import *
import time
import json
import requests
from gpiozero import MotionSensor
import threading
import os

class PresenceSensor:
    def __init__(self, PIR_info, resource_catalog_file):
        self.resource_catalog = json.load(open(resource_catalog_file))
        request_string = f'http://{self.resource_catalog["ip_address"]}:{self.resource_catalog["ip_port"]}/broker'
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["name"]
        self.port = rjson["port"]

        info = json.load(open(PIR_info))
        self.topic = info["servicesDetails"][0]["topic"]
        self.topic_direct = info["servicesDetails"][0].get("topic_direct")
        self.clientID = info["ID"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, None)
        self.pir = MotionSensor(17)
        self.PIR_info = PIR_info

    def register(self):
        request_string = f'http://{self.resource_catalog["ip_address"]}:{self.resource_catalog["ip_port"]}/registerResource'
        data = json.load(open(self.PIR_info))
        try:
            r = requests.put(request_string, json.dumps(data, indent=4))
            print(f'Response: {r.text}')
        except:
            print("An error occurred during registration")

    def start(self):
        self.client.start()

    def stop(self):
        self.client.stop()

    def motion_callback(self):
        now = time.time()
        msg = {
            "bn": self.clientID,
            "e": {
                "n": "ped_sens",
                "u": "Boolean",
                "t": now,
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
                    "t": now,
                    "v": "pedestrian",
                    "source": "direct"
                }
            }
            self.client.myPublish(self.topic_direct, direct_msg)
            print("Published directly:\n" + json.dumps(direct_msg))

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    resource_catalog_path = os.path.normpath(os.path.join(script_dir, "..", "resource_catalog_info.json"))
    pir_info_path = os.path.normpath(os.path.join(script_dir, "PIR_info.json"))

    pres = PresenceSensor(pir_info_path, resource_catalog_path)
    threading.Thread(target=pres.register, daemon=True).start()
    pres.start()

    try:
        pres.pir.when_motion = pres.motion_callback
        while True:
            time.sleep(1)
    finally:
        pres.stop()