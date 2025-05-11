import time
import adafruit_dht
import board  # Importa la libreria board per i pin GPIO
from MyMQTT import *
import json
import os
import threading
import requests


class TempSensor:
    def __init__(self, DHT_info, resource_catalog_file):
        # Retrieve broker info from service catalog
        self.resource_catalog = json.load(open(resource_catalog_file))
        request_string = 'http://' + self.resource_catalog["ip_address"] + ':' \
                         + self.resource_catalog["ip_port"] + '/broker'
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["name"]
        self.port = rjson["port"]

        # Details about sensor
        self.DHT_info = DHT_info
        info = json.load(open(self.DHT_info))
        self.topic = info["servicesDetails"][0]["topic"]
        self.clientID = info["ID"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, None)

        # Set GPIO pin for the DHT11 sensor (using board.D24)
        DHT_pin = board.D24  # GPIO pin where the data pin of the DHT11 is connected
        # Initialize DHT11 sensor using board.D24 for the GPIO pin
        self.sensor = adafruit_dht.DHT11(DHT_pin)
    
    def register(self):
        request_string = 'http://' + self.resource_catalog["ip_address"] + ':' + self.resource_catalog["ip_port"] + '/registerResource'
        data = json.load(open(self.DHT_info))
        try:
            r = requests.put(request_string, json.dumps(data, indent=4))
            print(f'Response: {r.text}')
        except:
            print("An error occurred during registration")

    
    def start(self):
        self.client.start()

    def stop(self):
        self.client.stop()

    def background(self):
        while True:
            self.register()
            time.sleep(10)

    def foreground(self):
        self.start()

    def publish(self, temperature , humidity):
        timestamp = time.time()
        message = {
            "bn": self.clientID,
            "bt": timestamp,
            "e": [{
                "n": "temperature",
                "u": "C",
                "v": temperature
            }]
        }
        self.MQTTClient.myPublish(TEMP_TOPIC, message)
        #print(f"Published to {TEMP_TOPIC}: {json.dumps(message)}")
        print(f"Temperature: {temperature}°C")

    def publish_humidity(self, humidity):
        timestamp = time.time()
        message = {
            "bn": f"{self.clientID}/humidity",
            "e": [{
                "n": "humidity",
                "u": "%",
                "v": humidity
            }
            ]
        }
        self.MQTTClient.myPublish(HUMIDITY_TOPIC, message)
        # print(f"Published to {HUMIDITY_TOPIC}: {json.dumps(message)}")
        print(f"Humidity: {humidity}%")


    def read_dht11_data(self):
        try:
            # Attempt to read data from the DHT11 sensor
            temperature = self.sensor.temperature
            humidity = self.sensor.humidity
            if temperature is not None and humidity is not None:
                self.publish(temperature , humidity)
            else:
                print("Failed to retrieve data from the sensor")
        except RuntimeError as e:
            print(f"DHT11 read error: {e}")

if __name__ == '__main__':
    # Lines to make automatically retrieve the path of resource_catalog_info.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    resource_catalog_path = os.path.join(script_dir, "..", "..", "resource_catalog", "resource_catalog_info.json")
    resource_catalog_path = os.path.normpath(resource_catalog_path)
    tempSensor_info_path = os.path.join(script_dir, "DHT11.json")
    tempSensor_info_path = os.path.normpath(tempSensor_info_path)
    sens = TempSensor(tempSensor_info_path, resource_catalog_path)
    print("Temperature and Humidity sensor ready... waiting for detection")

    b = threading.Thread(name='background', target=sens.background)
    f = threading.Thread(name='foreground', target=sens.foreground)

    b.start()
    f.start()

    try:
        while True:
            sens.read_dht11_data() # Read data from the DHT11 sensor
            time.sleep(5)  # Wait for 5 seconds before the next reading
    except KeyboardInterrupt:
        print("Program interrupted.")
    finally:
        sens.stop()


# try:
#     while True:
#         read_dht11_data()  
#         time.sleep(5)  # Wait for 5 seconds before the next reading

# except KeyboardInterrupt:
#     print("Program interrupted.")
# finally:
#     publisher.stop()
#     sensor.exit()
