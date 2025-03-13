from gpiozero import MotionSensor
from time import time, sleep
from MyMQTT import MyMQTT
import json

# MQTT Configuration
BROKER = "mqtt.eclipseprojects.io"
PORT = 1883
CLIENT_ID = "PIR_Sensor_01"
TOPIC = "/pir/motion"

class PIRPublisher:
    def __init__(self, clientID, broker, port):
        self.clientID = clientID
        self.broker = broker
        self.port = port
        self.PIRClient = MyMQTT(clientID, broker, port, None)
    
    def start(self):
        self.PIRClient.start()

    def stop(self):
        self.PIRClient.stop()

    def publish_motion(self):
        timestamp = time()
        message = {
            "bn": f"{self.clientID}/pir",
            "e": [{
                "n": "motion",
                "u": "boolean",
                "t": timestamp,
                "v": True  # Movement detected
            }]
        }
        self.PIRClient.myPublish(TOPIC, message)
        # print(f"Published to {TOPIC}: {json.dumps(message)}")

# Initialize PIR sensor
pir = MotionSensor(17)
print("PIR sensor ready... waiting for motion")

# Initialize MQTT publisher
publisher = PIRPublisher(CLIENT_ID, BROKER, PORT)
publisher.start()

last_motion_time = 0

try:
    while True:
        if pir.motion_detected:
            now = time()
            if now - last_motion_time > 1:  # Avoid duplicate readings
                print(f"Motion detected! ({now:.2f})")
                publisher.publish_motion()
                last_motion_time = now
        sleep(0.1)  # Adjusted sleep for responsiveness

except KeyboardInterrupt:
    print("\nInterrupted by user. Exiting...")
finally:
    publisher.stop()
