from MyMQTT import *
import time
import datetime
import json
import requests
# non so quali siano le libreire che servono per il led :)
from gpiozero import LED
import Adafruit_DHT
import threading
import urllib.request

#led its just a subscriber, subscribe to two different topics depending on what you need to do with the lights
# general topic for cars , and specific topic for pedestrian button 

#reads what LedManager sends and act depending on it
class LEDLights:
    def __init__(self, led_info, resource_catalog_file):
        # Retrieve broker info from resource catalog
        self.resource_catalog = json.load(open(resource_catalog_file))
        request_string = 'http://' + self.resource_catalog["ip_address"] + ':' \
                         + self.resource_catalog["ip_port"] + '/broker'
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["name"]
        self.port = rjson["port"]
        # Details about sensor

        self.led_info = led_info
        info = json.load(open(self.led_info))
        self.topic = info["servicesDetails"][0]["topic"]
        self.topic_zone = info["servicesDetails"][0]["topic_zone"]

        self.clientID = info["Name"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, self)
        
        self.standard_cycle = info["standard_duty_cycle"]
        self.vulnerable_cycle = info["vulnerable_duty_cycle"]
        self.pedestrian_cycle = info["pedestrian_duty_cycle"]
        self.emergency_cycle = info["emergency_duty_cycle"]


        #intersection 1

        self.NS_led1green = LED(24)  # Car green light
        self.NS_led1red = LED(22)  # Car red light
        self.WE_led1green = LED(23)  # Pedestrian green light
        self.WE_led1red = LED(18)  # Pedestrian red light

        #intersection2

        self.NS_led2green = LED()  # Car green light
        self.NS_led2red = LED()  # Car red light
        self.WE_led2green = LED()  # Pedestrian green light
        self.WE_led2red = LED()  # Pedestrian red light


    def register(self):#register handles the led registration to resource catalogs
        # Send registration request to Resource Catalog Server
        request_string = 'http://' + self.resource_catalog["ip_address"] + ':' \
                         + self.resource_catalog["ip_port"] + '/registerResource'
        data = json.load(open(self.led_info))
        try:
            r = requests.put(request_string, json.dumps(data, indent=4))
            print(f'Response: {r.text}')
        except:
            print("An error occurred during registration")


    def start(self):
        self.client.start()
        time.sleep(3)
        self.client.mySubscribe(self.topic)
        self.client.mySubscribe(self.topic_zone)

    def stop(self):
        self.client.unsubscribe()
        time.sleep(3)
        self.client.stop()

    def notify(self, topic, payload):
        payload = json.loads(payload)
        print(f'Message received: {payload}\n Topic: {topic}')
        cycle = self.standard_cycle  # Default cycle
        emergency = False
        intersection = None
        direction = None
        if topic == self.topic_zone + '/1':
            # /1 we are in the first intersection
            intersection = 1
            if payload["e"]["v"] == 'vulnerable_pedestrian':
            #do what you need to do with the lights in the intersection 1 when a vulnerable pedestrian is detected
                cycle = self.vulnerable_cycle
            elif payload["e"]["v"] == 'pedestrian':
            #do what you need to do with the lights in the intersection 1 when a pedestrian is detected
                cycle =self.pedestrian_cycle
            elif payload["e"]["v"] == 'car_infraction':
            #put a variable infraction to true
                pass

        elif topic == self.topic_zone + '/2':
            # /2 we are in the second intersection
            intersection = 2
            if payload["e"]["v"] == 'vulnerable_pedestrian':
            #do what you need to do with the lights in the intersection 1 when a vulnerable pedestrian is detected
                cycle = self.vulnerable_cycle
            elif payload["e"]["v"] == 'pedestrian':
            #do what you need to do with the lights in the intersection 1 when a pedestrian is detected
                cycle = self.pedestrian_cycle
            elif payload["e"]["v"] == 'car_infraction':
            #put a variable infraction to true
                pass

        elif topic == self.topic_zone + '/emergency':
            #emergency in the intersection 1 and 2
            emergency = True
            cycle = self.emergency_cycle
            direction = payload["e"]["v"]

        self.led_cycle_v2(cycle = cycle ,emergency= emergency, intersection = intersection , direction= direction ) #regular led cycle


    def led_cycle_v2(self ,intersection ,  cycle, emergency , direction = None):

        if emergency:
            print("EMERGENCY!")  #emergecy only in NS direction
            for i in [1, 2]:
                getattr(self, f"NS_led{i}green").on()
                getattr(self, f"NS_led{i}red").off()
                getattr(self, f"WE_led{i}green").off()
                getattr(self, f"WE_led{i}red").on()
            time.sleep(cycle)

        NS_green = getattr(self, f"NS_led{intersection}green", None)
        NS_red = getattr(self, f"NS_led{intersection}red", None)
        WE_green = getattr(self, f"WE_led{intersection}green", None)
        WE_red = getattr(self, f"WE_led{intersection}red", None)

        if None in (NS_green, NS_red, WE_green, WE_red):
            print(f"Error: LED of intersection {intersection} not found.")
            return

        while True:
            time.sleep(cycle)
            if NS_green.is_lit:
                NS_green.off()
                NS_red.on()
                WE_green.on()
                WE_red.off()

            else:
                NS_green.on()
                NS_red.off()
                WE_green.off()
                WE_red.on()

        
    def background(self):
        while True:
            self.register()
            time.sleep(10)

    def foreground(self):
        self.start()


if __name__ == '__main__':
    #bisogna essere sicuri che il file resource_catalog_info.json sia accesibile anche se è in un'altra cartella
    # Riposta: per questo si dovrebbe poter usare la libreria os
    led = LEDLights('LEDsimoneProvaInfo.json', 'resource_catalog_info.json')

    b = threading.Thread(name='background', target=led.background)
    f = threading.Thread(name='foreground', target=led.foreground)

    b.start()
    f.start()

    while True:
        time.sleep(1)

    # led.stop()
