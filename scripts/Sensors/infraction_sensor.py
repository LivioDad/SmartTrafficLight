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
        self.topic_red = info["servicesDetails"][0]["topic_red"]
        self.topic_infraction =  info["servicesDetails"][0]["topic_infraction"]
        self.clientID = info["ID"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, None)
        self.distance_threshold = info["distance_threshold"]
        self.warning_cooldown = info["warning_cooldown"]

        self.last_warning_time = 0

        self.pir  = DistanceSensor(echo=27, trigger=22)
        self.converter = { "NS" : 1 , "WE" : 2}

        
        self.current_car_time = time.time()
        # Avvia il simulatore di auto in un thread separato
        self.simulator_running = True
        self.simulator_thread = threading.Thread(target=self.car_simulator, daemon=True)
        self.simulator_thread.start()




    def register(self):
        request_string = 'http://' + self.resource_catalog["ip_address"] + ':' + self.resource_catalog["ip_port"] + '/registerResource'
        data = json.load(open(self.infractionSensor_info))
        try:
            r = requests.put(request_string, json.dumps(data, indent=4))
            print(f'Response: {r.text}')
        except:
            print("An error occurred during registration")

    def notify(self, topic, payload):
        payload = json.loads(payload)
        print(f'Message received: {payload}\n Topic: {topic}')
        intersection = payload["intersection"]
        direction = payload["e"]["v"]
        infraction_time = payload["e"]["t"]
        cycle = payload["e"]["c"]

        car_time = self.current_car_time

        if car_time > self.last_warning_time and car_time < (self.last_warning_time + cycle):
            self.publish_red_infraction(direction ,intersection , infraction_time )

    def publish_red_infraction(self , direction , intersection , infraction_time):
        msg = {
                "intersection" : intersection,
                "timestamp" : infraction_time,
                "station": self.converter[direction]
            }
        self.client.myPublish(self.topic_infraction, msg)
        print("Published:\n" + json.dumps(msg))


    def car_simulator(self):
        while self.simulator_running:
            self.current_car_time = time.time()
            time.sleep(2)


    def start(self):
        self.client.start()

    def stop(self):
        self.client.stop()

    def presence_callback(self, time):
        distance = self.pir.distance * 100  # Convert to cm
        print(f"Distance: {distance:.2f} cm")
        
        # If the distance is less than the threshold, publish MQTT message
        if distance < self.distance_threshold:
            activation_time = time
            if activation_time - self.last_warning_time > self.warning_cooldown:  # Check if enough time has passed
                print(f"Vehicle detected! ({time.time():.2f})")
            self.last_warning_time = activation_time  # Update the last warning time
        
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
    print("Distance sensor ready... waiting for detection")

    b = threading.Thread(name='background', target=pres.background)
    f = threading.Thread(name='foreground', target=pres.foreground)

    b.start()
    f.start()

    try:
        while True:
            pres.presence_callback(time.time())
            time.sleep(0.5)

        #pause()

    finally:
        pres.stop()
