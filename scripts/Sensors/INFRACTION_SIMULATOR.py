from MyMQTT import *
import time
import datetime
import json
import requests
import threading
import os

class SimulatedInfractionSensor:
    def __init__(self, infractionSensor_info, resource_info):
        self.broker = "mqtt.eclipseproject.io"
        self.port = "1883"

        self.infractionSensor_info = infractionSensor_info
        info = json.load(open(self.infractionSensor_info))
        self.topic = info["servicesDetails"][0]["topic"]
        self.topic_status = info["servicesDetails"][0]["topic_status"]
        self.topic_infraction = info["servicesDetails"][0]["topic_infraction"]
        self.clientID = info["ID"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, self)
        self.distance_threshold = info["distance_threshold"]
        self.warning_cooldown = info["warning_cooldown"]
        self.isred = False
        self.intersection = None
        self.direction = None
        self.converter = { "NS": 1, "WE": 2 }

    def publish_red_infraction(self):
        msg = {
            "intersection": self.intersection,
            "timestamp": time.time(),
            "station": self.converter.get(self.direction, 0)
        }
        self.client.myPublish(self.topic_infraction, msg)
        print("Messaggio pubblicato:\n" + json.dumps(msg, indent=2))

    def start(self):
        self.client.start()
        self.client.mySubscribe(self.topic_status)

    def stop(self):
        self.client.stop()

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    resource_catalog_path = os.path.normpath(os.path.join(script_dir, "..", "..", "resource_catalog", "resource_catalog_info.json"))
    infractionSensor_info_path = os.path.normpath(os.path.join(script_dir, "infractionSensor_info.json"))

    sensor = SimulatedInfractionSensor(infractionSensor_info_path, resource_catalog_path)

    while True:
        ok = input("ok? ")
        if ok == "ok":
            SimulatedInfractionSensor.publish_red_infraction

