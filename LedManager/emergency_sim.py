from MyMQTT import *
import time
import json
import requests
import threading
import os



class EmergecySystem:
    def __init__(self,emergecy_info , resource_catalog_file):
        # Retrieve broker info from service catalog
        self.resource_catalog = json.load(open(resource_catalog_file))
        request_string = 'http://' + self.resource_catalog["ip_address"] + ':' \
                         + self.resource_catalog["ip_port"] + '/broker'
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["name"]
        self.port = rjson["port"]

        # Details about emergecy
        self.info = emergecy_info
        info = json.load(open(self.info))
        self.topic = info["servicesDetails"][0]["topic"]
        self.clientID = info["ID"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, None)



    def register(self):
        """Periodically register the sensor in the resource catalog."""
        request_string = f'http://{self.resource_catalog["ip_address"]}:{self.resource_catalog["ip_port"]}/registerResource'
        data = json.load(open(self.info))
        try:
            r = requests.put(request_string, json.dumps(data, indent=4))
            print(f'Response: {r.text}')
        except Exception as e:
            print(f'Error during registration: {e}')

    def start(self):
        """Start MQTT connection."""
        self.client.start()

    def stop(self):
        """Stop MQTT connection and terminate the thread."""
        self.client.stop()

    def background(self):
        while True:
            self.register()
            time.sleep(10)

    def foreground(self):
        self.start()

    def call_emergency(self , zone , direction):
        msg = {
            "zone" : zone,
            "direction" : direction,
            "time" : time.time()
        }
        self.client.myPublish(self.topic, msg)
        print("published\n" + json.dumps(msg))

    def menu(self):
        while True:
            print("\n---Emergency System Menu ---")
            zone = input("Enter zone (we only have A ...): ")
            direction = input("Enter direction (NS or WE): ")
            self.call_emergency(zone, direction)


if __name__ == '__main__':
    # Automatically retrieve the path of JSON config files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    resource_catalog_path = os.path.join(script_dir, "..", "..", "resource_catalog", "resource_catalog_info.json")
    resource_catalog_path = os.path.normpath(resource_catalog_path)
    emergency_info_path = os.path.join(script_dir, "emergency_sim_info.json")
    emergency_info_path = os.path.normpath(emergency_info_path)

    em = EmergecySystem(resource_catalog_path)


    b = threading.Thread(name='background', target=em.background)
    f = threading.Thread(name='foreground', target=em.foreground)
    m = threading.Thread(name='menu', target=em.menu)

    b.start()
    f.start()
    m.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down")
        em.stop()