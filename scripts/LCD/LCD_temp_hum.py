import time
import json
from LCD_config import LCD
from MyMQTT import MyMQTT

# MQTT broker configuration
BROKER = "mqtt.eclipseprojects.io"
PORT = 1883
CLIENT_ID = "LCD_Display_01"
TEMP_TOPIC = "/sensor/temperature"
HUMIDITY_TOPIC = "/sensor/humidity"

class LCDSubscriber:
    def __init__(self, clientID, broker, port, temp_topic, hum_topic):
        """
        Initializes the LCD display and MQTT client.
        
        Parameters:
        - clientID: Unique ID for the MQTT client
        - broker: MQTT broker address
        - port: MQTT broker port
        - temp_topic: MQTT topic for temperature data
        - hum_topic: MQTT topic for humidity data
        """
        self.clientID = clientID
        self.broker = broker
        self.port = port
        self.temp_topic = temp_topic
        self.hum_topic = hum_topic
        self.temperature = None  # Stores the latest temperature value
        self.humidity = None  # Stores the latest humidity value

        # Initialize the LCD (Raspberry Pi revision 2, I2C address 0x27, backlight enabled)
        self.lcd = LCD(2, 0x27, True)
        self.lcd.message("Waiting for", 1)
        self.lcd.message("sensor data...", 2)

        # Configure the MQTT client
        self.MQTTClient = MyMQTT(clientID, broker, port, self)

    def start(self):
        """Starts the MQTT connection and subscribes to the temperature and humidity topics."""
        self.MQTTClient.start()
        self.MQTTClient.mySubscribe(self.temp_topic)
        self.MQTTClient.mySubscribe(self.hum_topic)

    def stop(self):
        """Stops the MQTT connection and clears the LCD."""
        self.MQTTClient.stop()
        self.lcd.clear()

    def notify(self, topic, payload):
        """
        Callback function triggered when an MQTT message is received.

        Parameters:
        - topic: The topic of the received message
        - payload: The message content (JSON encoded)
        """
        try:
            # Decode the received JSON message
            message_decoded = json.loads(payload)
            if "e" in message_decoded and len(message_decoded["e"]) > 0:
                event = message_decoded["e"][0]  # Extract event data
                value = event["v"]  # Extract the sensor value

                if topic == self.temp_topic:
                    self.temperature = value
                elif topic == self.hum_topic:
                    self.humidity = value

                # Display updated temperature and humidity values on LCD
                self.update_display()

        except Exception as e:
            print(f"⚠ Error processing message: {e}")

    def update_display(self):
        """Updates the LCD with the latest temperature and humidity values."""
        self.lcd.clear()
        temp_text = f"Temp: {self.temperature:.1f}C" if self.temperature is not None else "Temp: --.-C"
        hum_text = f"Hum: {self.humidity:.1f}%" if self.humidity is not None else "Hum: --.-%"
        self.lcd.message(temp_text, 1)
        self.lcd.message(hum_text, 2)

# Initialize and start the LCD MQTT subscriber
lcd_subscriber = LCDSubscriber(CLIENT_ID, BROKER, PORT, TEMP_TOPIC, HUMIDITY_TOPIC)
lcd_subscriber.start()

try:
    while True:
        time.sleep(1)  # Keep the script running and listening for messages

except KeyboardInterrupt:
    print("\nStopping LCD MQTT Subscriber...")
    lcd_subscriber.stop()
    print("Stopped.")
