from MyMQTT import *
import time
import json
import requests
from gpiozero import DistanceSensor
import threading
import os

# This scripts reads the json file containing the status of the traffic lights, in this case "light1_status.json"
# and interpolates this information with the distance sensor to detect if a vehicle is passing on a red light.

class InfractionSensor:
    def __init__(self, infractionSensor_info, resource_catalog_file):
        # Retrieve broker info from service catalog
        self.resource_catalog = json.load(open(resource_catalog_file))
        self.status_file_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Lights", "light1_status.json"))
        request_string = 'http://' + self.resource_catalog["ip_address"] + ':' + \
                         self.resource_catalog["ip_port"] + '/broker'
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["name"]
        self.port = rjson["port"]

        # Details about sensor
        self.infractionSensor_info = infractionSensor_info
        info = json.load(open(self.infractionSensor_info))
        self.topic = info["servicesDetails"][0]["topic"]
        self.topic_status = info["servicesDetails"][0]["topic_status"]
        self.topic_infraction = info["servicesDetails"][0]["topic_infraction"]
        self.clientID = info["ID"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, self)
        self.distance_threshold = info["distance_threshold"]
        self.warning_cooldown = info["warning_cooldown"]            # Needed not to have duplicated infractions (can be set in the info.json file)
        self.infraction_cooldown = info.get("infraction_cooldown", 2)

        # Initialize variables
        self.status_NS = None
        self.status_WE = None

        # Direction on which the sensor is placed
        self.observed_direction = "NS"

        self.last_warning_time = 0
        self.pir = DistanceSensor(echo=27, trigger=22)
        self.converter = { "NS": 2, "WE": 1 }

    def register(self):
        request_string = 'http://' + self.resource_catalog["ip_address"] + ':' + self.resource_catalog["ip_port"] + '/registerResource'
        data = json.load(open(self.infractionSensor_info))
        try:
            r = requests.put(request_string, json.dumps(data, indent=4))
            print(f'Response: {r.text}')
        except:
            print("An error occurred during registration")
    
    def read_status_from_file(self):
        try:
            with open(self.status_file_path, "r") as f:
                data = json.load(f)
                self.status_NS = data.get("NS")
                self.status_WE = data.get("WE")
                self.intersection = data.get("intersection", "unknown")
        except Exception as e:
            print(f"[STATUS FILE ERROR] {e}")

    def publish_red_infraction(self):
        msg = {
            "intersection": self.intersection,
            "timestamp": time.time(),
            "station": self.converter[self.observed_direction]
        }
        self.client.myPublish(self.topic_infraction, msg)
        print("Published: " + json.dumps(msg) + "\non topic: " + self.topic_infraction)

    def stop(self):
        self.client.stop()

    def start(self):
        self.client.start()

    def presence_callback(self):
        self.read_status_from_file()
        distance = self.pir.distance * 100  # cm
        now = time.time()
        if distance < self.distance_threshold:
            # Check if the traffic light is red on the observed direction
            if self.observed_direction == "NS" and self.status_NS == "red_light":
                if now - self.last_warning_time > self.infraction_cooldown:
                    print(f"Vehicle detected in NS on RED! ({now:.2f})")
                    self.publish_red_infraction()
                    self.last_warning_time = now
                else:
                    print(f"Vehicle detected in NS on RED but cooldown not expired ({now - self.last_warning_time:.2f}s)")
            elif self.observed_direction == "WE" and self.status_WE == "red_light":
                if now - self.last_warning_time > self.infraction_cooldown:
                    print(f"Vehicle detected in WE on RED! ({now:.2f})")
                    self.publish_red_infraction()
                    self.last_warning_time = now
                else:
                    print(f"Vehicle detected in WE on RED but cooldown not expired ({now - self.last_warning_time:.2f}s)")
            else:
                print(f"Vehicle detected in {self.observed_direction}, but light is GREEN or unknown")

        time.sleep(0.1)

    def background(self):
        while True:
            self.register()
            time.sleep(10)

    def foreground(self):
        self.start()

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    resource_catalog_path = os.path.join(script_dir, "..", "resource_catalog", "resource_catalog_info.json")
    resource_catalog_path = os.path.normpath(resource_catalog_path)
    infractionSensor_info_path = os.path.join(script_dir, "infraction_sensor_info.json")
    infractionSensor_info_path = os.path.normpath(infractionSensor_info_path)
    pres = InfractionSensor(infractionSensor_info_path, resource_catalog_path)
    print("Distance sensor ready... waiting for detection")

    b = threading.Thread(name='background', target=pres.background)
    f = threading.Thread(name='foreground', target=pres.foreground)

    b.start()
    f.start()

    try:
        while True:
            pres.presence_callback()
            time.sleep(0.5)
    finally:
        pres.stop()