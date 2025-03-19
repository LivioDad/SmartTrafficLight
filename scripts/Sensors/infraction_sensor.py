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




class InfractionSensor:
    def __init__(self, infractionSensor_info, resource_catalog_file):
        # Retrieve broker info from service catalog
        self.resource_catalog = json.load(open(resource_catalog_file))
        request_string = 'http://' + self.resource_catalog["ip_address"] + ':' \
                         + self.resource_catalog["ip_port"] + '/broker'
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["name"]
        self.port = rjson["port"]

        # Details about sensor
        self.infractionSensor_info = infractionSensor_info
        info = json.load(open(self.infractionSensor_info))
        self.topic = info["servicesDetails"][0]["topic"]
        self.clientID = info["ID"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, None)
        self.distance_threshold = info["distance_threshold"]
        self.warning_cooldown = info["warning_cooldown"]

        self.last_warning_time = 0

        self.pir  = DistanceSensor(echo=27, trigger=22)


    def register(self):
        request_string = 'http://' + self.resource_catalog["ip_address"] + ':' + self.resource_catalog["ip_port"] + '/registerResource'
        data = json.load(open(self.infractionSensor_info))
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
        distance = self.pir.distance * 100  # Convert to cm
        print(f"Distance: {distance:.2f} cm")
        
        # If the distance is less than the threshold, publish MQTT message
        if distance < self.distance_threshold:
            current_time = time.time()
            if current_time - self.last_warning_time > self.warning_cooldown:  # Check if enough time has passed

                msg = {
                    "bn": self.clientID,
                    "e": {
                        "n": "mov_sens",
                        "u": "Boolean",
                        "t": time.time(),
                        "v": True,
                    }
                }
            self.client.myPublish(self.topic, msg)
            print("published\n" + json.dumps(msg))
            print(f"Motion detected! ({time.time():.2f})")


            self.last_warning_time = current_time  # Update the last warning time
        
        time.sleep(0.1)  # Wait time to avoid an overly fast loop
       

        
    def background(self):
        while True:
            self.register()
            time.sleep(10)

    def foreground(self):
        self.start()

if __name__ == '__main__':
    # Lines to make automatically retrieve the path of resource_catalog_info.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    resource_catalog_path = os.path.join(script_dir, "..", "..", "resource_catalog", "resource_catalog_info.json")
    resource_catalog_path = os.path.normpath(resource_catalog_path)
    infractionSensor_info_path = os.path.join(script_dir, "infractionSensor_info.json")
    infractionSensor_info_path = os.path.normpath(infractionSensor_info_path)
    pres = InfractionSensor(infractionSensor_info_path, resource_catalog_path)
    print("PIR sensor ready... waiting for motion")

    b = threading.Thread(name='background', target=pres.background)
    f = threading.Thread(name='foreground', target=pres.foreground)

    b.start()
    f.start()

    try:
        pres.pir.when_motion = pres.motion_callback

        #pause()

    finally:
        pres.stop()
