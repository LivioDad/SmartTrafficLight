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

#led its just a subscriber, subscribet to twp different topics depending on what you need to do with the lights
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
        self.topic = info["servicesDetails"][0]["topic"] # topic dedicated to led
        self.topic_zone = info["servicesDetails"][0]["topic_zone"] # topic common to all zone
        self.clientID = info["Name"]
        self.cycle = info["standard_duty_cycle"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, self)

        #intersection 1

        self.car_led1green = LED(24)  # Car green light
        self.car_led1red = LED(22)  # Car red light
        self.ped_led1green = LED(23)  # Pedestrian green light
        self.ped_led1red = LED(18)  # Pedestrian red light

        #intersection2

        self.car_led2green = LED()  # Car green light
        self.car_led2red = LED()  # Car red light
        self.ped_led2green = LED()  # Pedestrian green light
        self.ped_led2red = LED()  # Pedestrian red light

        # LED functioning control sensor
        self.led_ctrl = Adafruit_DHT.DHT11  # Temperature & humidity sensor
        self.led_ctrl_pin = 25
        # Thingspeak details
        self.base_url = info["Thingspeak"]["base_url"]
        self.key = info["Thingspeak"]["key"]
        self.url_read = info["Thingspeak"]["url_read"]

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
        cycle = self.cycle  # Default cycle
        emergency = False
        intersection = None
        if topic == self.topic_zone + '/1':
            # /1 we are in the first intersection
            intersection = 1
            if payload["e"]["v"] == 'vulnerable_pedestrian':
            #do what you need to do with the lights in the intersection 1 when a vulnerable pedestrian is detected
                cycle = 10 
            elif payload["e"]["v"] == 'pedestrian':
            #do what you need to do with the lights in the intersection 1 when a pedestrian is detected
                cycle = 7
            elif payload["e"]["v"] == 'car_infraction':
            #put a variable infraction to true
                pass

        elif topic == self.topic_zone + '/2':
            # /2 we are in the second intersection
            intersection = 2
            if payload["e"]["v"] == 'vulnerable_pedestrian':
            #do what you need to do with the lights in the intersection 1 when a vulnerable pedestrian is detected
                cycle = 10
            elif payload["e"]["v"] == 'pedestrian':
            #do what you need to do with the lights in the intersection 1 when a pedestrian is detected
                cycle = 7
            elif payload["e"]["v"] == 'car_infraction':
            #put a variable infraction to true
                pass

        elif topic == self.topic + '/emergency':
            #emergency in the intersection 1 and 2
            emergency = True

        self.led_cycle_v2(cycle = cycle ,emergency= emergency, intersection = intersection ) #regular led cycle


    def led_cycle_v2(self ,intersection ,  cycle, emergency):

        if emergency:
            print("EMERGENCY!")
            for i in [1, 2]:
                getattr(self, f"car_led{i}green").on()
                getattr(self, f"car_led{i}red").off()
                getattr(self, f"ped_led{i}green").off()
                getattr(self, f"ped_led{i}red").on()
            time.sleep(20)

        car_green = getattr(self, f"car_led{intersection}green", None)
        car_red = getattr(self, f"car_led{intersection}red", None)
        ped_green = getattr(self, f"ped_led{intersection}green", None)
        ped_red = getattr(self, f"ped_led{intersection}red", None)

        if None in (car_green, car_red, ped_green, ped_red):
            print(f"Error: LED of intersection {intersection} not found.")
            return

        while True:
            time.sleep(cycle)
            if car_green.is_lit:
                car_green.off()
                car_red.on()
                ped_green.on()
                ped_red.off()

            else:
                car_green.on()
                car_red.off()
                ped_green.off()
                ped_red.on()


    def thingspeak_post(self, val): #non so come funziona Thingspeak :)
        URL = self.base_url #This is unchangeble
        KEY = self.key #This is the write key API of your channels

    	#field one corresponds to the first graph, field2 to the second ... 
        HEADER='&field2={}'.format(val)
        
        NEW_URL = URL+KEY+HEADER
        URL_read = self.url_read
        print("Temperature data have been sent to Thingspeak\n" + URL_read)
        data = urllib.request.urlopen(NEW_URL)
        print(data)
        
    def background(self):
        while True:
            self.register()
            time.sleep(10)

    def foreground(self):
        self.start()


if __name__ == '__main__':
    #bisogna essere sicuri che il file resource_catalog_info.json sia accesibile anche se è in un'altra cartella
    led = LEDLights('LEDsimoneProvaInfo.json', 'resource_catalog_info.json')

    b = threading.Thread(name='background', target=led.background)
    f = threading.Thread(name='foreground', target=led.foreground)

    b.start()
    f.start()

    while True:
        time.sleep(1)

    # led.stop()
