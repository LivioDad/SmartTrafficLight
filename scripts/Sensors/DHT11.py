import time
import adafruit_dht
import board  # Importa la libreria board per i pin GPIO
from MyMQTT import MyMQTT
import json

# MQTT Configuration
BROKER = "mqtt.eclipseprojects.io"
PORT = 1883
CLIENT_ID = "DHT11_Sensor_01"
TEMP_TOPIC = "/sensor/temperature"
HUMIDITY_TOPIC = "/sensor/humidity"

# Set GPIO pin for the DHT11 sensor (using board.D24)
DHT_PIN = board.D24  # GPIO pin where the data pin of the DHT11 is connected

# Initialize the MQTT publisher
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
        print(f"Published to {TEMP_TOPIC}: {json.dumps(message)}")

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
        print(f"Published to {HUMIDITY_TOPIC}: {json.dumps(message)}")

# Start the MQTT client
publisher = DHTPublisher(CLIENT_ID, BROKER, PORT)
publisher.start()

# Initialize DHT11 sensor using board.D24 for the GPIO pin
sensor = adafruit_dht.DHT11(DHT_PIN)

def read_dht11_data():
    try:
        # Attempt to read data from the DHT11 sensor
        temperature = sensor.temperature
        humidity = sensor.humidity
        if temperature is not None and humidity is not None:
            publisher.publish_temperature(temperature)
            publisher.publish_humidity(humidity)
        else:
            print("Failed to retrieve data from the sensor")
    except RuntimeError as e:
        print(f"DHT11 read error: {e}")

try:
    while True:
        read_dht11_data()  # Read data from the DHT11 sensor
        time.sleep(5)  # Wait for 5 seconds before the next reading

except KeyboardInterrupt:
    print("Program interrupted.")
finally:
    publisher.stop()
    sensor.exit()
