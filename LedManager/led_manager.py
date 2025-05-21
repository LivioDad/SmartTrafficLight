from MyMQTT import *
import time
import json
import requests
import threading
import os

class LedManager:
    def __init__(self, ledmanager_info, resource_catalog_info):
        # Retrieve broker info (port and broker name) from resource catalog info,calling a GET from resource_catalog_server
        self.resource_catalog_info = json.load(open(resource_catalog_info))
        #retrievs IP address and Port od the service_catalog_server from service_catalog_info.json to use it to do a GET
        request_string = 'http://' + self.resource_catalog_info["ip_address"] + ':' + self.resource_catalog_info["ip_port"] + '/broker'
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["name"]
        self.port = rjson["port"]

        # Details about sensor
        self.led_manager_file = ledmanager_info
        info = json.load(open(self.led_manager_file))
        for s in info["serviceDetails"]:
            if s["serviceType"]=='MQTT':
                self.topicS = s["topic_subscribe"] #topic to which it is subscribed to receive messages from sensors
                self.topicP = s["topic_publish"] #topic on which it publishes messages for the activations of leds
                self.topicE = s["topic_emergency"] #topic on which it publishes messages for the acrivations of leds in emergency cases
        self.clientID = info["Name"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, self) #configure MQTT

    def register(self):
        '''
        periodicallty registers itself to the resource catalog to confirm it is active
        '''
        request_string = 'http://' + self.resource_catalog_info["ip_address"] + ':' + self.resource_catalog_info["ip_port"] + '/registerResource'
        data = json.load(open(self.led_manager_file))
        try:
            r = requests.put(request_string, json.dumps(data, indent=4))
            print(f'Response: {r.text}')
        except:
            print("An error occurred during registration")

    # Method to START and SUBSCRIBE
    def start(self):
        self.client.start()
        time.sleep(3)  # Timer of 3 second (to deal with asynchronous)
        #useful to avoid the risk of subscribung to a topic before the connection with the broker starts
        self.client.mySubscribe(self.topicS)  #subscribe to subscribeTopic (to receive all messages from sensor in A zone)
        self.client.mySubscribe(self.topicE)  

    # Method to UNSUBSCRIBE and STOP
    def stop(self):
        self.client.unsubscribe()
        time.sleep(3) #to allow the client to unsubscribe from topics
        self.client.stop()

    def notify(self, topic, payload):
        # print(f"Received message on topic {topic}: {payload}")
        '''
        when it receives a message from a sensor, the message is processed, the message is in the form:
        msg = {
            "bn": self.clientID (identifies the sensor that sended the message its in the .json file of the sensor),
            "e": {
                "n": "vul_button/ped_sens/mov_sens",
                "u": "Boolean",
                "t": time.time(),
                "v": True
            }
        }

        '''
        if topic.startswith(self.topicS[:-1]):  # Removes the '#' and compares:
            messageReceived = json.loads(payload)
            print(messageReceived)
            bn = messageReceived["bn"] #identifies the sensor that sended the message
            id = bn.split('_')
            sensorType = id[1] #sensor type (b for the button , c for the movement sensor , I for infraction sensor)
            trafficLightID = id[2] #id of the Led associated to the sensor (1 or 2 depending on the intersection)
            obj = 0
            if messageReceived["e"]["n"] == "vul_button": #if the message its from a button (vulnerable pedestrian)
                obj = "vulnerable_pedestrian"
                if messageReceived["e"]["v"]: #if the value of the event its true (not 0)
                    specific_topic = self.topicP + '/' + trafficLightID
                    self.publish(specific_topic, obj) #publishes a messages to that led with the object detected, a vulnerable pedestrian
                    print("LED were notified of a vulnerable pedestrian")

            elif messageReceived["e"]["n"] == "ped_sens": #if the message its from a movement sensor (pedestrian)
                obj = "pedestrian"
                if messageReceived["e"]["v"]: #if the value of the event its true (not 0)
                    specific_topic = self.topicP + '/' + trafficLightID
                    self.publish(specific_topic, obj) #publishes a messages to that led with the object detected, a pedestrian

            # elif messageReceived["e"]["n"] == "mov_sens": #if the message its from a button (infraction)
            #     obj = "car_infraction"
            #     if messageReceived["e"]["v"]: #if the value of the event its true (not 0)
            #         specific_topic = self.topicP + '/' + trafficLightID  #non so ancora dove mandare il messaggio, in che topic
            #         self.publish(specific_topic, obj) #publishes a messages to that led with the object detected, a car infraction

        elif topic == self.topicE:
            messageReceived = json.loads(payload)
            if "direction" in messageReceived and "zone" in messageReceived:
                direction = messageReceived["direction"]
                zone = messageReceived["zone"]
                msg = {
                    "bn": zone,
                    "e": {
                        "n": "emergency",
                        "u": "direction",
                        "t": time.time(),
                        "v": direction
                    }
                }
                self.client.myPublish(self.topicP, msg)
                print("published\n" + json.dumps(msg) + '\nOn topic: ' + f'{self.topicP}')
                
    def publish(self, topicP, obj):
        '''
        if the sensor detects a pedestrian/vulnerable pedestrian/infraction car, the manager publishes under topicPublish + the id of the led
        '''
        msg = {
            "bn": self.clientID,
            "e": {
                "n": "led",
                "u": "detection",
                "t": time.time(),
                "v": obj
            }
        }
        self.client.myPublish(topicP, msg)
        print("published\n" + json.dumps(msg) + '\nOn topic: ' + f'{topicP}')

    def background(self):
        #periodically register itself every 10 seconds to the resource catalog
        while True:
            self.register()
            time.sleep(10)

    def foreground(self):
        self.start()


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))  # Get the directory of the current script
    led_manager_info_path = os.path.join(script_dir, 'led_manager_info.json')
    #resource_catalog_info_path = os.path.join(os.path.dirname(script_dir), 'resource_catalog', 'resource_catalog_info.json')
    resource_catalog_info_path = os.path.join(script_dir, 'resource_catalog_info.json')

    ledMan = LedManager(led_manager_info_path, resource_catalog_info_path)

    b = threading.Thread(name='background', target=ledMan.background)
    f = threading.Thread(name='foreground', target=ledMan.foreground)

    b.start() #activate the backgorund periodically register
    f.start() #activate the subscirpiton to MQTT topics

    while True:
        time.sleep(3)

    # ledMan.stop()
