from gpiozero import DistanceSensor
import time
from MyMQTT import MyMQTT
import json

# MQTT Configuration
BROKER = "mqtt.eclipseprojects.io"
PORT = 1883
CLIENT_ID = "Distance_Sensor_01"
TOPIC = "/distance/alert"

# Set the threshold distance in cm
DISTANCE_THRESHOLD = 30  # Set the distance threshold (in cm)

# Set the cooldown period (in seconds) for warnings
WARNING_COOLDOWN = 3  # Publish a warning every 3 seconds (settable)

# Set up the pins for the HC-SR04 sensor
sensor = DistanceSensor(echo=27, trigger=22)

# Initialize the MQTT publisher
class DistancePublisher:
    def __init__(self, clientID, broker, port):
        self.clientID = clientID
        self.broker = broker
        self.port = port
        self.MQTTClient = MyMQTT(clientID, broker, port, None)
    
    def start(self):
        self.MQTTClient.start()

    def stop(self):
        self.MQTTClient.stop()

    def publish_alert(self, distance):
        timestamp = time.time()
        message = {
            "bn": f"{self.clientID}/distance",
            "e": [{
                "n": "alert",
                "u": "cm",
                "t": timestamp,
                "v": distance
            }]
        }
        self.MQTTClient.myPublish(TOPIC, message)
        print(f"Published to {TOPIC}: {json.dumps(message)}")

# Start the MQTT client
publisher = DistancePublisher(CLIENT_ID, BROKER, PORT)
publisher.start()

# Track the last warning time
last_warning_time = 0

# Start monitoring and print the distance
try:
    while True:
        distance = sensor.distance * 100  # Convert to cm
        print(f"Distance: {distance:.2f} cm")
        
        # If the distance is less than the threshold, publish MQTT message
        if distance < DISTANCE_THRESHOLD:
            current_time = time.time()
            if current_time - last_warning_time > WARNING_COOLDOWN:  # Check if enough time has passed
                publisher.publish_alert(distance)  # Publish the alert to MQTT
                last_warning_time = current_time  # Update the last warning time
        
        time.sleep(0.1)  # Wait time to avoid an overly fast loop

except KeyboardInterrupt:
    print("Measurement interrupted.")
finally:
    publisher.stop()
