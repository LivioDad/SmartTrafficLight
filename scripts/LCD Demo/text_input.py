import time
import json
from LCD import LCD
from MyMQTT import MyMQTT

# MQTT broker configuration
BROKER = "mqtt.eclipseprojects.io"
PORT = 1883
CLIENT_ID = "LCD_Display_01"
TOPIC = "/lcd/message"

class LCDSubscriber:
    def __init__(self, clientID, broker, port, topic):
        """Initializes the LCD display and MQTT client."""
        self.clientID = clientID
        self.broker = broker
        self.port = port
        self.topic = topic

        # Initialize LCD (for Raspberry Pi revision 2, I2C address 0x27, backlight enabled)
        self.lcd = LCD(2, 0x27, True)  
        self.lcd.message("Waiting for", 1)
        self.lcd.message("MQTT messages...", 2)

        # Configure MQTT client
        self.MQTTClient = MyMQTT(clientID, broker, port, self)

    def start(self):
        """Starts the MQTT connection and subscribes to the topic."""
        self.MQTTClient.start()
        self.MQTTClient.mySubscribe(self.topic)

    def stop(self):
        """Stops the MQTT connection and clears the LCD."""
        self.MQTTClient.stop()
        self.lcd.clear()

    def notify(self, topic, payload):
        """Callback function triggered when an MQTT message is received."""
        try:
                message_decoded = json.loads(payload)  # Decode JSON message
                if "e" in message_decoded and len(message_decoded["e"]) > 0:
                        event = message_decoded["e"][0]  # Extract event data
                if event["n"] == "lcd_message":  
                        text = event["v"]  
                        print(f"Received: {text}")

                        # Display the message on the LCD
                        self.lcd.clear()
                        self.lcd.message(text[:16], 1)  # Show first 16 characters on line 1
                        self.lcd.message(text[16:32], 2)  # Show next 16 characters on line 2 (if any)

        except Exception as e:
                print(f"⚠ Error processing message: {e}")

# Initialize and start the LCD MQTT subscriber
lcd_subscriber = LCDSubscriber(CLIENT_ID, BROKER, PORT, TOPIC)
lcd_subscriber.start()

try:
    while True:
        time.sleep(1)  # Keep the script running and listening for messages

except KeyboardInterrupt:
    print("\nStopping LCD MQTT Subscriber...")
    lcd_subscriber.stop()
    print("Stopped.")
