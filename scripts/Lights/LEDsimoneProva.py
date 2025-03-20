from MyMQTT import *
import time
import datetime
import json
import requests
# non so quali siano le libreire che servono per il led :)
from gpiozero import LED
import threading
import os


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

        self.topic = led_info["servicesDetails"][0]["topic"]
        self.topic_zone = led_info["servicesDetails"][0]["topic_zone"]

        self.clientID = info["Name"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, self)
        
        self.standard_cycle = led_info["standard_duty_cycle"]
        self.vulnerable_cycle = led_info["vulnerable_duty_cycle"]
        self.pedestrian_cycle = led_info["pedestrian_duty_cycle"]
        self.emergency_cycle = led_info["emergency_duty_cycle"]

        self.intersection_number = led_info["ID"].split('_')[2]
        self.pins = led_info["pins"]


        #intersection 1

        self.NS_green = LED(self.pins["NS_green"])  # Car green light
        self.NS_red = LED(self.pins["NS_red"])  # Car red light
        self.WE_green = LED(self.pins["WE_green"])  # Pedestrian green light
        self.WE_red = LED(self.pins["WE_red"])  # Pedestrian red light

        #intersection2


    def register(self):#register handles the led registration to resource catalogs
        # Send registration request to Resource Catalog Server
        request_string = 'http://' + self.resource_catalog["ip_address"] + ':' \
                         + self.resource_catalog["ip_port"] + '/registerResource'
        data = self.led_info
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
        direction = None
        if topic == self.topic_zone + f'/{self.intersection_number}':
            # /1 we are in the first intersection
            if payload["e"]["v"] == 'vulnerable_pedestrian':
            #do what you need to do with the lights in the intersection 1 when a vulnerable pedestrian is detected
                cycle = self.vulnerable_cycle
            elif payload["e"]["v"] == 'pedestrian':
            #do what you need to do with the lights in the intersection 1 when a pedestrian is detected
                cycle =self.pedestrian_cycle
            elif payload["e"]["v"] == 'car_infraction':
            #put a variable infraction to true
                pass


        elif topic == self.topic_zone + '/emergency':
            #emergency in the intersection 1 and 2
            emergency = True
            cycle = self.emergency_cycle
            direction = payload["e"]["v"]

        self.led_cycle_v2(cycle = cycle ,emergency= emergency , direction= direction ) #regular led cycle


    def led_cycle_v2(self ,  cycle, emergency , direction = None):

        if emergency:
            if direction == 'NS':
                self.NS_green.on()
                self.NS_red.off()
                self.WE_green.off()
                self.WE_red.on()
            elif direction == 'WE':
                self.NS_green.off()
                self.NS_red.on()
                self.WE_green.on()
                self.WE_red.off()
            time.sleep(cycle)

        while True:
            time.sleep(cycle)
            if self.NS_green.is_lit:
                self.NS_green.off()
                self.NS_red.on()
                self.WE_green.on()
                self.WE_red.off()

            else:
                self.NS_green.on()
                self.NS_red.off()
                self.WE_green.off()
                self.WE_red.on()

        
    def background(self):
        while True:
            self.register()
            time.sleep(10)

    def foreground(self):
        self.start()


if __name__ == '__main__':
    #bisogna essere sicuri che il file resource_catalog_info.json sia accesibile anche se è in un'altra cartella
    # Riposta: per questo si dovrebbe poter usare la libreria os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    resource_catalog_path = os.path.join(script_dir, "..", "..", "resource_catalog", "resource_catalog_info.json")
    resource_catalog_path = os.path.normpath(resource_catalog_path)
    led_info_path = os.path.join(script_dir, "LEDsimoneProvaInfo.json")
    led_info_path = os.path.normpath(led_info_path)


    info = json.load(open(led_info_path))
    info_led1 = json.dumps(info["led_intersection"][0])
    info_led2 = json.dumps(info["led_intersection"][1])

    led1 = LEDLights(info_led1, 'resource_catalog_info.json')
    led2 = LEDLights(info_led2, 'resource_catalog_info.json')

    b1 = threading.Thread(name='background', target=led1.background)
    f1 = threading.Thread(name='foreground', target=led1.foreground)

    b2 = threading.Thread(name='background', target=led2.background)
    f2 = threading.Thread(name='foreground', target=led2.foreground)

    b1.start()
    f1.start()

    b2.start()
    f2.start()

    while True:
        time.sleep(1)

    # led.stop()
