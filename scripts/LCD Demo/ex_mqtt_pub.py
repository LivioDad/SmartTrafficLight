
import time
import json
from MyMQTT import MyMQTT

# MQTT broker configuration
BROKER = "mqtt.eclipseprojects.io"
PORT = 1883
CLIENT_ID = "Console_Publisher"
TOPIC = "/lcd/message"  

class ConsolePublisher:
    def __init__(self, clientID, broker, port, topic):
        """Initializes the MQTT publisher."""
        self.clientID = clientID
        self.broker = broker
        self.port = port
        self.topic = topic

        # Initialize the MQTT client
        self.MQTTClient = MyMQTT(clientID, broker, port, None)

    def start(self):
        """Starts the MQTT connection."""
        self.MQTTClient.start()

    def stop(self):
        """Stops the MQTT connection."""
        self.MQTTClient.stop()

    def publish_message(self, message):
        """Publishes a message to the MQTT topic."""
        mqtt_payload = {
            "e": [{
                "n": "lcd_message",
                "v": message
            }]
        }
        self.MQTTClient.myPublish(self.topic, mqtt_payload)
        print(f"Sent: {message}")

# Initialize the publisher
publisher = ConsolePublisher(CLIENT_ID, BROKER, PORT, TOPIC)
publisher.start()

try:
    while True:
        # Ask the user to input a message
        user_message = input("✍ Enter a message to display on LCD: ")

        # Publish the message if it's not empty
        if user_message.strip():
            publisher.publish_message(user_message)
        else:
            print("⚠ Message cannot be empty!")

except KeyboardInterrupt:
    print("\nStopping MQTT Publisher...")
    publisher.stop()
    print("Stopped.")
