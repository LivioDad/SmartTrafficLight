import time
import adafruit_dht
import board
from MyMQTT import MyMQTT
import json
import os
import threading
import requests

# MQTT Configuration
TEMP_TOPIC = "/sensor/temperature"
HUMIDITY_TOPIC = "/sensor/humidity"

class TempSensor:
    def __init__(self, DHT_info, resource_catalog_file):
        self.DHT_info = DHT_info
        # Load catalog and get broker
        with open(resource_catalog_file) as f:
            self.resource_catalog = json.load(f)
        r = requests.get(f"http://{self.resource_catalog['ip_address']}:{self.resource_catalog['ip_port']}/broker")
        broker_data = r.json()
        self.broker = broker_data["name"]
        self.port = broker_data["port"]

        # Load sensor info
        with open(DHT_info) as f:
            info = json.load(f)
        self.clientID = info["ID"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, None)
        self.topic = info["servicesDetails"][0]["topic"]  # usually "/sensor"
        self.sensor = adafruit_dht.DHT11(board.D24)

    def register(self):
        try:
            with open(self.DHT_info) as f:
                data = json.load(f)
            r = requests.put(
                f"http://{self.resource_catalog['ip_address']}:{self.resource_catalog['ip_port']}/registerResource",
                json.dumps(data, indent=4))
            print(f"Response: {r.text}")
        except Exception as e:
            print(f"Registration error: {e}")

    def start(self):
        self.client.start()

    def stop(self):
        self.client.stop()

    def background(self):
        while True:
            self.register()
            time.sleep(10)

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
        self.client.myPublish(TEMP_TOPIC, message)
        print(f"Temperature: {temperature}°C")

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
        self.client.myPublish(HUMIDITY_TOPIC, message)
        print(f"Humidity: {humidity}%")

    def read_dht11_data(self):
        try:
            temperature = self.sensor.temperature
            humidity = self.sensor.humidity
            if temperature is not None and humidity is not None:
                self.publish_temperature(temperature)
                self.publish_humidity(humidity)
            else:
                print("Failed to retrieve data from the sensor")
        except RuntimeError as e:
            print(f"DHT11 read error: {e}")

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    resource_catalog_path = os.path.join(script_dir, "..", "..", "resource_catalog", "resource_catalog_info.json")
    tempSensor_info_path = os.path.join(script_dir, "DHT11.json")

    sens = TempSensor(tempSensor_info_path, resource_catalog_path)
    print("Temperature and Humidity sensor ready... waiting for detection")

    b = threading.Thread(name='background', target=sens.background)
    f = threading.Thread(name='foreground', target=sens.start)

    b.start()
    f.start()

    try:
        while True:
            sens.read_dht11_data()
            time.sleep(5)
    except KeyboardInterrupt:
        print("Program interrupted.")
    finally:
        sens.stop()