from MyMQTT import *
import time
import json
import requests
from gpiozero import LED
import threading
import os

class LEDLights:
    def __init__(self, led_info, resource_catalog_file):
        # Retrieve broker info from the resource catalog
        self.resource_catalog = json.load(open(resource_catalog_file))
        request_string = 'http://' + self.resource_catalog["ip_address"] + ':' + self.resource_catalog["ip_port"] + '/broker'
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["name"]
        self.port = rjson["port"]

        # Load LED configuration
        led_info = led_info["LedInfo"]
        self.led_info = led_info
        self.topic = led_info["servicesDetails"][0]["topic"]
        self.topic_zone = led_info["servicesDetails"][0]["topic_zone"]
        self.topic_red = led_info["servicesDetails"][0]["topic_red"]

        self.clientID = led_info["Name"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, self)

        # Load duty cycles
        self.standard_cycle = led_info["standard_duty_cycle"]
        self.vulnerable_cycle = led_info["vulnerable_road_users_duty_cycle"]
        self.pedestrian_cycle = led_info["pedestrian_duty_cycle"]
        self.emergency_cycle = led_info["emergency_duty_cycle"]

        self.intersection_number = led_info["ID"].split('_')[2]
        self.pins = led_info["pins"]

        # Initialize LED lights
        self.NS_green = LED(self.pins["NS_green"])
        self.NS_red = LED(self.pins["NS_red"])
        self.WE_green = LED(self.pins["WE_green"])
        self.WE_red = LED(self.pins["WE_red"])

        # Start the standard traffic light cycle
        self.start_standard_cycle()

    def register(self):
        """ Periodically registers the LED system to the resource catalog. """
        request_string = 'http://' + self.resource_catalog["ip_address"] + ':' + self.resource_catalog["ip_port"] + '/registerResource'
        data = self.led_info
        try:
            r = requests.put(request_string, json.dumps(data, indent=4))
            print(f'Response: {r.text}')
        except:
            print("An error occurred during registration")

    def start(self):
        """ Starts the MQTT client and subscribes to topics. """
        self.client.start()
        time.sleep(3)
        self.client.mySubscribe(self.topic)
        self.client.mySubscribe(self.topic_zone)

    def stop(self):
        """ Unsubscribes and stops the MQTT client. """
        self.client.unsubscribe()
        time.sleep(3)
        self.client.stop()

    def notify(self, topic, payload):
        """ Handles incoming MQTT messages and triggers the appropriate LED cycle. """
        payload = json.loads(payload)
        print(f'Message received: {payload}\n Topic: {topic}')
        cycle = self.standard_cycle  # Default cycle
        emergency = False
        direction = None

        if topic == self.topic_zone + f'/{self.intersection_number}':
            if payload["e"]["v"] == 'vulnerable_pedestrian':
                cycle = self.vulnerable_cycle
                print("Vulnerable pedestrian cycle activated")
            elif payload["e"]["v"] == 'pedestrian':
                cycle = self.pedestrian_cycle
            elif payload["e"]["v"] == 'car_infraction':
                pass  # Handle infractions if needed

        elif topic == self.topic_zone + '/emergency':
            emergency = True
            cycle = self.emergency_cycle
            direction = payload["e"]["v"]

        # Run the LED cycle in a separate thread
        threading.Thread(target=self.led_cycle, args=(cycle, emergency, direction)).start()

    def led_cycle(self, cycle, emergency, direction=None):
        """ Controls the LED lights based on the received event. """
        if emergency:
            if direction == 'NS':
                self.NS_green.on()
                self.NS_red.off()
                self.WE_green.off()
                self.WE_red.on()
                self.publish_red_light("WE" , cycle)
            elif direction == 'WE':
                self.NS_green.off()
                self.NS_red.on()
                self.WE_green.on()
                self.WE_red.off()
                self.publish_red_light("NS" , cycle)
            time.sleep(cycle)
            return

        for _ in range(2):
            time.sleep(cycle)
            if self.NS_green.is_lit:
                self.NS_green.off()
                self.NS_red.on()
                self.WE_green.on()
                self.WE_red.off()
                self.publish_red_light("NS" ,cycle)

            else:
                self.NS_green.on()
                self.NS_red.off()
                self.WE_green.off()
                self.WE_red.on()
                self.publish_red_light("WE" ,cycle)

                
    def publish_red_light(self , direction , cycle):
        msg = {
            "intersection": self.intersection_number,
            "e": {
                "n": "red_light",
                "u": "direction",
                "t": time.time(),
                "v": direction,
                "c" : cycle
            }
        }
        self.client.myPublish(self.topic_red, msg)
        print("Published:\n" + json.dumps(msg))
        
    def background(self):
        """ Periodically registers the LED system every 10 seconds. """
        while True:
            self.register()
            time.sleep(10)

    def foreground(self):
        """ Starts the MQTT client and listens for messages. """
        self.start()


if __name__ == '__main__':
    # Load JSON configuration files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir2 = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    resource_catalog_path = os.path.join(parent_dir2,"SmartTrafficLight", "resource_catalog", "resource_catalog_info.json")
    led_info_path = os.path.join(script_dir, "LED_semaforo1_info.json")

    info = json.load(open(led_info_path))

    led = LEDLights(info, resource_catalog_path)

    # Start background and foreground threads
    threading.Thread(name='background', target=led.background).start()
    threading.Thread(name='foreground', target=led.foreground).start()

    while True:
        time.sleep(1)