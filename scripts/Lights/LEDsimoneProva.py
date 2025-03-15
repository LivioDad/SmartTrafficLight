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
        self.timer = info["timer"]  # Timer
        self.cycle = info["standard_duty_cycle"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, self)


        self.car_led1 = LED(24)  # Car green light
        self.car_led2 = LED(22)  # Car red light
        self.ped_led1 = LED(23)  # Pedestrian green light
        self.ped_led2 = LED(18)  # Pedestrian red light

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
        if topic == self.topic_zone + '/1':
            # /1 we are in the first intersection
            if payload["e"]["v"] == 'vulnerable_pedestrian':
            #do what you need to do with the lights in the intersection 1 when a vulnerable pedestrian is detected
            #ex : self.led_cycle_vulnerable_pedestrian()
                pass
            elif payload["e"]["v"] == 'pedestrian':
            #do what you need to do with the lights in the intersection 1 when a pedestrian is detected
                pass
            elif payload["e"]["v"] == 'car_infraction':
            #put a variable infraction to true
                pass

        elif topic == self.topic_zone + '/2':
            # /2 we are in the second intersection
            if payload["e"]["v"] == 'vulnerable_pedestrian':
            #do what you need to do with the lights in the intersection 1 when a vulnerable pedestrian is detected
            #ex : self.led_cycle_vulnerable_pedestrian()
                pass
            elif payload["e"]["v"] == 'pedestrian':
            #do what you need to do with the lights in the intersection 1 when a pedestrian is detected
                pass
            elif payload["e"]["v"] == 'car_infraction':
            #put a variable infraction to true
                pass
        self.standard_led_cycle() #regular led cycle based on timer

    def standard_led_cycle(self):
        # Start regular functioning cycle
        timer = self.timer #total time the led works
        while timer > 0:
            timer -= self.cycle #timer - (how long green/red last in a led, in standard situations)
            time.sleep(self.cycle) #pause the program for a cycle, representing the time a led stays in a state
            if self.car_led1.is_lit: #if the green for the cars is on:
                self.car_led1.off() #turn off car green
                self.car_led2.on()#turn on car red
                self.ped_led1.on()#turn on pedestrian green
                self.ped_led2.off()#turn on car red

            else:#if the green for cars is off (meaning its red):
                self.car_led1.on() #turn on green for cars
                self.car_led2.off() #turn off red for cars
                self.ped_led1.off()#turn off green for pedestrians
                self.ped_led2.on()#turn on red for pedestrians

            #do the same for the other intersection

        
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
