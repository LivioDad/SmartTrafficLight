from MyMQTT import *
import time
import datetime
import json
import requests
from gpiozero import DistanceSensor
import threading
import urllib.request
import requests
import threading
import json
import random
import os

class SIM_InfractionSensor:
    def __init__(self, infractionSensor_info, resource_catalog_file):
        # Retrieve broker info from service catalog
        self.resource_catalog = json.load(open(resource_catalog_file))
        request_string = 'http://' + self.resource_catalog["ip_address"] + ':' \
                         + self.resource_catalog["ip_port"] + '/broker'
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["name"]
        self.port = rjson["port"]
        self.intersection = "1"
        self.direction = "NS"
        self.status = "red_light"

        # Details about sensor
        self.infractionSensor_info = infractionSensor_info
        info = json.load(open(self.infractionSensor_info))
        self.topic = info["servicesDetails"][0]["topic"]
        self.topic_status = info["servicesDetails"][0]["topic_status"]
        self.topic_infraction =  info["servicesDetails"][0]["topic_infraction"]
        self.clientID = info["ID"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, self)
        self.distance_threshold = info["distance_threshold"]
        self.warning_cooldown = info["warning_cooldown"]
        self.isred = False

        self.last_warning_time = 0
        self.converter = { "NS" : 1 , "WE" : 2}

    def notify(self, topic, payload):
        return

    def register(self):
        request_string = 'http://' + self.resource_catalog["ip_address"] + ':' + self.resource_catalog["ip_port"] + '/registerResource'
        data = json.load(open(self.infractionSensor_info))
        try:
            r = requests.put(request_string, json.dumps(data, indent=4))
            print(f'Response: {r.text}')
        except:
            print("An error occurred during registration")

    def publish_red_infraction(self):
        msg = {
                "intersection" : self.intersection,
                "timestamp" : time.time(),
                "station": self.converter[self.direction]
            }
        self.client.myPublish(self.topic_infraction, msg)
        print("Published: " + json.dumps(msg) + "\non topic: " + self.topic_infraction)

    def start(self):
        self.client.start()
        self.client.mySubscribe(self.topic_status)

    def stop(self):
        self.client.stop()

if __name__ == '__main__':
    # Lines to make automatically retrieve the path of resource_catalog_info.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    resource_catalog_path = os.path.join(script_dir, "..", "..", "resource_catalog", "resource_catalog_info.json")
    resource_catalog_path = os.path.normpath(resource_catalog_path)
    infractionSensor_info_path = os.path.join(script_dir, "infractionSensor_info.json")
    infractionSensor_info_path = os.path.normpath(infractionSensor_info_path)
    Simulator = SIM_InfractionSensor(infractionSensor_info_path, resource_catalog_path)
    Simulator.start()

    print("Distance sensor ready... waiting for detection")

    while True:
        command = input("Type 'ok' to send mqtt message: ")
        if command == "ok":
            Simulator.publish_red_infraction()
        

