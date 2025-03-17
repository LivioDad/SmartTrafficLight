from MyMQTT import *
import time
import datetime
import json
import requests
from gpiozero import Button
from signal import pause
import threading
import urllib.request
import requests
import threading
import json

import random


class PedestrianButton:
    def __init__(self, button_info, resource_catalog_file):
        # Retrieve broker info from service catalog
        self.resource_catalog = json.load(open(resource_catalog_file))
        request_string = 'http://' + self.resource_catalog["ip_address"] + ':' \
                         + self.resource_catalog["ip_port"] + '/broker'
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["name"]
        self.port = rjson["port"]

        # Details about sensor
        self.button_info = button_info
        info = json.load(open(self.button_info))
        self.topic = info["servicesDetails"][0]["topic"]
        self.clientID = info["ID"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, None)
        self.but = Button(17)

    def register(self):#register handles the led registration to resource catalogs
        request_string = 'http://' + self.rc["ip_address"] + ':' + self.rc["ip_port"] + '/registerResource'
        data = json.load(open(self.button_info))
        try:
            r = requests.put(request_string, json.dumps(data, indent=4))
            print(f'Response: {r.text}')
        except:
            print('An error occurred during registration')

    def start(self):
        self.client.start()

    def stop(self):
        self.client.stop()

    def press_callback(self):
        # Callback function for button press, this message is sent to LedManagerA that its subsciberd to the topic
        msg = {
            "bn": self.clientID,
            "e": {
                "n": "vul_button",
                "u": "Boolean",
                "t": time.time(),
                "v": True
            }
        }
        self.client.myPublish(self.topic, msg)
        print("published\n" + json.dumps(msg))


    def background(self):
        while True:
            self.register()
            time.sleep(10)

    def foreground(self):
        self.start()


if __name__ == '__main__':
    button = PedestrianButton('Button2_info.json', 'resource_catalog_info.json')

    b = threading.Thread(name='background', target=button.background)
    f = threading.Thread(name='foreground', target=button.foreground)

    b.start()
    f.start()

    try:
        button.but.when_pressed = button.press_callback

        pause()

    finally:
        button.stop()
