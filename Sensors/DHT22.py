import time
import adafruit_dht
import board
from MyMQTT import MyMQTT
import json
import os
import requests

# Load configuration from JSON
script_dir = os.path.dirname(os.path.abspath(__file__))
sensor_info_path = os.path.join(script_dir, "DHT22_info.json")
#catalog_info_path = os.path.normpath(os.path.join(script_dir, "..", "resource_catalog", "resource_catalog_info.json"))
catalog_info_path = os.path.join(script_dir, "resource_catalog_info.json")


with open(sensor_info_path) as f:
    config = json.load(f)
with open(catalog_info_path) as f:
    catalog = json.load(f)

# Get broker info from catalog
request_string = f"http://{catalog['ip_address']}:{catalog['ip_port']}/broker"
r = requests.get(request_string)
rjson = json.loads(r.text)
BROKER = rjson["name"]
PORT = rjson["port"]

clientID = config["ID"]
zone = config["zone"]
gpio_pin_str = config["gpio_pin"]
DHT_PIN = getattr(board, gpio_pin_str)

# Load topics from config
topics = config["servicesDetails"][0]
TEMP_TOPIC = topics["topic_temperature"]
HUMIDITY_TOPIC = topics["topic_humidity"]
PREDICTOR_TOPIC = topics["topic_predictor"]

class DHTPublisher:
    def __init__(self, clientID, broker, port):
        self.clientID = clientID
        self.broker = broker
        self.port = port
        self.MQTTClient = MyMQTT(clientID, broker, port, None)

    def start(self):
        self.MQTTClient.start()

    def stop(self):
        self.MQTTClient.stop()

    def publish_temperature(self, temperature):
        timestamp = time.time()
        message = {
            "bn": f"{self.clientID}/temperature",
            "e": [{
                "n": "temperature",
                "u": "C",
                "t": timestamp,
                "v": temperature
            }]
        }
        self.MQTTClient.myPublish(TEMP_TOPIC, message)
        # print(f"Temperature: {temperature}°C")

    def publish_humidity(self, humidity):
        timestamp = time.time()
        message = {
            "bn": f"{self.clientID}/humidity",
            "e": [{
                "n": "humidity",
                "u": "%",
                "t": timestamp,
                "v": humidity
            }]
        }
        self.MQTTClient.myPublish(HUMIDITY_TOPIC, message)
        # print(f"Humidity: {humidity}%")

    def publish_predictor(self, temperature, humidity):
        timestamp = time.time()
        message = {
            "bn": self.clientID,
            "bt": timestamp,
            "e": [
                {"n": "temperature", "u": "C", "v": temperature},
                {"n": "humidity", "u": "%", "v": humidity}
            ]
        }
        self.MQTTClient.myPublish(PREDICTOR_TOPIC, message)
        print(f"Published: Temp: {temperature}°C, Humidity: {humidity}%")

    def register(self, sensor_info_path, catalog):
        try:
            with open(sensor_info_path) as f:
                data = json.load(f)
            url = f"http://{catalog['ip_address']}:{catalog['ip_port']}/registerResource"
            r = requests.put(url, json.dumps(data, indent=4))
            print(f"Registered to resource catalog. Response: {r.text}")
        except Exception as e:
            print(f"Registration failed: {e}")


# MAIN

publisher = DHTPublisher(clientID, BROKER, PORT)
publisher.register(sensor_info_path, catalog)
publisher.start()

sensor = adafruit_dht.DHT22(DHT_PIN)

def read_DHT22_data():
    try:
        temperature = sensor.temperature
        humidity = sensor.humidity
        if temperature is not None and humidity is not None:
            publisher.publish_temperature(temperature)
            publisher.publish_humidity(humidity)
            publisher.publish_predictor(temperature, humidity)
        else:
            print("Failed to retrieve data from the sensor")
    except RuntimeError as e:
        print(f"DHT22 read error: {e}")

try:
    while True:
        read_DHT22_data()
        time.sleep(5)

except KeyboardInterrupt:
    print("Program interrupted.")

finally:
    publisher.stop()
    sensor.exit()