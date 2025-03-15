from gpiozero import LED, Button
import time
from MyMQTT import MyMQTT
import json

# MQTT Configuration
BROKER = "mqtt.eclipseprojects.io"
PORT = 1883
CLIENT_ID = "Button_Press_01"
TOPIC = "/button/press"

# Set the GPIO pin for the button
BUTTON_PIN = 23 

# Define the LEDs on pins 5, 6, 7, and 8
ledg1 = LED(5)  # Green LED 1 (pin 5)
ledr1 = LED(6)  # Red LED 1 (pin 6)
ledg2 = LED(8)  # Green LED 2 (pin 8)
ledr2 = LED(7)  # Red LED 2 (pin 7)

# Create a button object
button = Button(BUTTON_PIN)

# Initialize the MQTT publisher
class ButtonPublisher:
    def __init__(self, clientID, broker, port):
        self.clientID = clientID
        self.broker = broker
        self.port = port
        self.MQTTClient = MyMQTT(clientID, broker, port, None)
    
    def start(self):
        self.MQTTClient.start()

    def stop(self):
        self.MQTTClient.stop()

    def publish_button_press(self):
        timestamp = time.time()
        message = {
            "bn": f"{self.clientID}/button",
            "e": [{
                "n": "button_press",
                "u": "boolean",
                "t": timestamp,
                "v": True  # Button pressed
            }]
        }
        self.MQTTClient.myPublish(TOPIC, message)
        print(f"Published to {TOPIC}: {json.dumps(message)}")

# Start the MQTT client
publisher = ButtonPublisher(CLIENT_ID, BROKER, PORT)
publisher.start()

# Track the last time a message was sent
last_message_time = 0

# Function for when the button is pressed
def on_button_press():
    global last_message_time
    current_time = time.time()

    # Only publish if at least 1 second has passed since the last message
    if current_time - last_message_time >= 1:
        print("Button pressed!")
        publisher.publish_button_press()  # Publish MQTT message when button is pressed
        last_message_time = current_time  # Update the last message time

        # Now control the LEDs in the desired sequence (only after button press)
        # r1 + g2 for 2 seconds
        ledr1.on()
        ledg2.on()
        print("r1 + g2 on")
        time.sleep(2)
        
        # Turn off r1 and g2, then turn on r2 + g1 for 2 seconds
        ledr1.off()
        ledg2.off()
        ledr2.on()
        ledg1.on()
        print("r2 + g1 on")
        time.sleep(2)
        
        # Turn off all LEDs after 2 seconds
        ledr2.off()
        ledg1.off()
        print("All LEDs off")

# Connect the functions to the button press event
button.when_pressed = on_button_press

try:
    while True:
        # Continuously monitor the button
        time.sleep(0.1)  # Slightly reduce the sleep time to keep responsiveness high

except KeyboardInterrupt:
    print("Program interrupted.")
finally:
    publisher.stop()
