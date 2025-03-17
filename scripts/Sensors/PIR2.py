from MyMQTT import *
import time
import datetime
import json
import requests
from gpiozero import MotionSensor
import signal
import threading

import urllib.request
import requests
import threading
import json

import random


class PresenceSensor:
    def __init__(self, PIR_info, resource_catalog_file):
        # Retrieve broker info from service catalog
        self.resource_catalog = json.load(open(resource_catalog_file))
        request_string = 'http://' + self.resource_catalog["ip_address"] + ':' \
                         + self.resource_catalog["ip_port"] + '/broker'
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["name"]
        self.port = rjson["port"]

        # Details about sensor
        self.PIR_info = PIR_info
        info = json.load(open(self.PIR_info))
        self.topic = info["servicesDetails"][0]["topic"]
        self.clientID = info["ID"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, None)

        self.pir = MotionSensor(27)


    def register(self):
        request_string = 'http://' + self.rc["ip_address"] + ':' + self.rc["ip_port"] + '/registerResource'
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
        msg = {
            "bn": self.clientID,
            "e": {
                "n": "ped_sens",
                "u": "Boolean",
                "t": time.time(),
                "v": True,
            }
        }
        self.client.myPublish(self.topic, msg)
        print("published\n" + json.dumps(msg))
        print(f"Motion detected! ({time():.2f})")

        
    def background(self):
        while True:
            self.register()
            time.sleep(10)

    def foreground(self):
        self.start()

if __name__ == '__main__':
    pres = PresenceSensor('PIR2_info.json', 'resource_catalog_info.json')
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
