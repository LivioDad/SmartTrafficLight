import time
import json
from MyMQTT import MyMQTT
from gpiozero import LED

# MQTT Configuration
BROKER = "mqtt.eclipseprojects.io"
PORT = 1883
CLIENT_ID = "LED_Control_01"
TOPIC = "/button/press"  # Listening for button press messages

# Define the LEDs on pins 5, 6, 7, and 8
ledg1 = LED(5)  # Green LED 1 (pin 5)
ledr1 = LED(6)  # Red LED 1 (pin 6)
ledg2 = LED(8)  # Green LED 2 (pin 8)
ledr2 = LED(7)  # Red LED 2 (pin 7)

class LEDSubscriber:
    def __init__(self, clientID, broker, port, topic):
        """Initializes the MQTT client and LED control."""
        self.clientID = clientID
        self.broker = broker
        self.port = port
        self.topic = topic

        # Configure MQTT client
        self.MQTTClient = MyMQTT(clientID, broker, port, self)

    def start(self):
        """Starts the MQTT connection and subscribes to the topic."""
        self.MQTTClient.start()
        self.MQTTClient.mySubscribe(self.topic)

    def stop(self):
        """Stops the MQTT connection."""
        self.MQTTClient.stop()

    def notify(self, topic, payload):
        """Callback function triggered when an MQTT message is received."""
        try:
            message_decoded = json.loads(payload)  # Decode JSON message
            if "e" in message_decoded and len(message_decoded["e"]) > 0:
                event = message_decoded["e"][0]  # Extract event data
                if event["n"] == "button_press" and event["v"]:  
                    print("📩 Button Press Detected!")
                    
                    # Perform the LED cycle (semaphore logic)
                    self.perform_led_cycle()
        except Exception as e:
            print(f"⚠ Error processing message: {e}")

    def perform_led_cycle(self):
        """Performs the LED traffic light cycle."""
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

# Initialize and start the LED MQTT subscriber
led_subscriber = LEDSubscriber(CLIENT_ID, BROKER, PORT, TOPIC)
led_subscriber.start()

try:
    while True:
        time.sleep(1)  # Keep the script running and listening for messages

except KeyboardInterrupt:
    print("\nStopping LED MQTT Subscriber...")
    led_subscriber.stop()
    print("Stopped.")