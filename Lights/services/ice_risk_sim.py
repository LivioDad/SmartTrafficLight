import time
import json
import os
from MyMQTT import MyMQTT
import requests

class IceRiskSimulator:
    def __init__(self, sim_info_path, resource_catalog_path):
        # Load resource catalog
        self.resource_catalog = json.load(open(resource_catalog_path))
        request_string = f"http://{self.resource_catalog['ip_address']}:{self.resource_catalog['ip_port']}/broker"
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["name"]
        self.port = rjson["port"]

        # Load simulator configuration
        self.sim_info = json.load(open(sim_info_path))
        self.topicP = self.sim_info["servicesDetails"][0]["topicP"]
        self.clientID = "ice_risk_simulator"

        # Initialize MQTT client
        self.client = MyMQTT(self.clientID, self.broker, self.port, self)

    def register(self):
        request_string = f"http://{self.resource_catalog['ip_address']}:{self.resource_catalog['ip_port']}/registerResource"
        try:
            r = requests.put(request_string, json.dumps(self.sim_info, indent=4))
            print(f"Registration response: {r.text}")
        except Exception as e:
            print("Error during registration:", e)

    def publish_ice_risk(self):
        value = 0.87  # fixed value that triggers LCD warning
        message = {
            "bn": self.clientID,
            "bt": int(time.time()),
            "e": [{
                "n": "ice_risk",
                "u": "%",
                "v": value
            }]
        }
        self.client.myPublish(self.topicP, message)
        print(f"Sent ice risk alert ({value}) on topic: {self.topicP}")

    def start(self):
        self.client.start()

    def stop(self):
        self.client.stop()

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    #resource_catalog_path = os.path.normpath(os.path.join(script_dir, "..", "..", "resource_catalog", "resource_catalog_info.json"))
    resource_catalog_path = os.path.join(script_dir, 'resource_catalog_info.json')
    sim_info_path = os.path.normpath(os.path.join(script_dir, "road_ice_info.json"))  # reuse the Predictor's config

    simulator = IceRiskSimulator(sim_info_path, resource_catalog_path)
    simulator.start()
    simulator.register()

    try:
        while True:
            cmd = input("Type 'ok' to send ice risk alert or 'exit' to quit: ").strip().lower()
            if cmd == "ok":
                simulator.publish_ice_risk()
            elif cmd == "exit":
                break
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user.")
    finally:
        simulator.stop()