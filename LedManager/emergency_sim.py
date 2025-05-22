from MyMQTT import *
import time
import json
import requests
import threading
import os

class EmergencySystem:
    def __init__(self, emergency_info, resource_catalog_file):
        self.resource_catalog = json.load(open(resource_catalog_file))
        request_string = f'http://{self.resource_catalog["ip_address"]}:{self.resource_catalog["ip_port"]}/broker'
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["name"]
        self.port = rjson["port"]

        info = json.load(open(emergency_info))
        self.topic = info["servicesDetails"][0]["topic"]
        self.topic_direct = info["servicesDetails"][0].get("topic_direct")
        self.clientID = info["ID"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, None)
        self.info = emergency_info

    def register(self):
        request_string = f'http://{self.resource_catalog["ip_address"]}:{self.resource_catalog["ip_port"]}/registerResource'
        data = json.load(open(self.info))
        try:
            r = requests.put(request_string, json.dumps(data, indent=4))
        except Exception as e:
            print(f'Error during registration: {e}')

    def start(self):
        self.client.start()

    def stop(self):
        self.client.stop()

    def call_emergency(self, zone, direction):
        now = time.time()
        msg = {
            "zone": zone,
            "direction": direction,
            "time": now
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
                    "v": "emergency",
                    "source": "direct",
                    "zone": zone,
                    "direction": direction
                }
            }
            self.client.myPublish(self.topic_direct, direct_msg)
            print("Published directly:\n" + json.dumps(direct_msg))

    def menu(self):
        while True:
            print("\n--- Emergency Menu ---")
            zone = input("Enter zone (e.g., A): ")
            direction = input("Enter direction (NS or WE): ")
            self.call_emergency(zone, direction)

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    resource_catalog_path = os.path.normpath(os.path.join(script_dir, "..", "resource_catalog", "resource_catalog_info.json"))
    emergency_info_path = os.path.normpath(os.path.join(script_dir, "emergency_sim_info.json"))

    em = EmergencySystem(emergency_info_path, resource_catalog_path)
    threading.Thread(target=em.register, daemon=True).start()
    em.start()
    em.menu()