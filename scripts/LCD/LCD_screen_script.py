import time
import json
from LCD_config import LCD
from MyMQTT import MyMQTT
import requests
import os


class LCDSubscriber:
    def __init__(self, led_manager_info, resource_catalog_info):
        """
        Initializes the LCD display and MQTT client by getting broker and topic details from the provided configuration files.

        Parameters:
        - led_manager_info: Path to the LED manager info JSON file
        - resource_catalog_info: Path to the resource catalog info JSON file
        """
        # Load the configuration files
        self.resource_catalog_info = json.load(open(resource_catalog_info))
        led_info = json.load(open(led_manager_info))

        # Request broker info from resource catalog
        request_string = f'http://{self.resource_catalog_info["ip_address"]}:{self.resource_catalog_info["ip_port"]}/broker'
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["name"]
        self.port = rjson["port"]

        # Extract topics from LED manager info
        for s in led_info["serviceDetails"]:
            if s["serviceType"] == 'MQTT':
                self.topicS = s["topic_subscribe"]
                self.topicP = s["topic_publish"]
                self.topicE = s["topic_emergency"]

        self.clientID = led_info["Name"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, self)

        # Initialize the LCD (Raspberry Pi revision 2, I2C address 0x27, backlight enabled)
        self.lcd = LCD(2, 0x27, True)
        self.lcd.message("Waiting for", 1)
        self.lcd.message("sensor data...", 2)

    def start(self):
        """Start MQTT client and subscribe to topics."""
        self.client.start()
        time.sleep(3)  # Allow time for the client to connect
        self.client.mySubscribe("SmartTrafficLight/Sensor/A/#")  # Subscribe to the sensor topic
        self.client.mySubscribe("SmartTrafficLight/Emergency")  # Subscribe to the emergency topic

    def stop(self):
        """Stop the MQTT client and unsubscribe from topics."""
        self.client.unsubscribe()
        time.sleep(3)  # Allow time to unsubscribe
        self.client.stop()

    def notify(self, topic, payload):
        """Callback method triggered when an MQTT message is received."""
        try:
            message_received = json.loads(payload)

            if topic.startswith("SmartTrafficLight/Sensor/A/"):  # Only process sensor messages
                if message_received["e"]["n"] == "vul_button" and message_received["e"]["v"]:
                    self.display_vulnerable_user()
                elif message_received["e"]["n"] == "ped_sens" and message_received["e"]["v"]:
                    self.display_crossing_user()

            elif topic == "SmartTrafficLight/Emergency":
                # Handle emergency messages
                direction = message_received["e"]["n"]
                self.display_emergency_message(direction)

        except Exception as e:
            print(f"⚠ Error processing message: {e}")

    def display_vulnerable_user(self):
        """Display the 'Vulnerable user crossing' message on the LCD for 5 seconds."""
        self.lcd.clear()
        self.lcd.message("Vulnerable user", 1)
        time.sleep(5)  # Keep the message for 5 seconds
        self.lcd.clear()  # Clear the display after 5 seconds

    def display_crossing_user(self):
        """Display the 'Pedestrian crossing' message on the LCD for 5 seconds."""
        self.lcd.clear()
        self.lcd.message("Pedestrian cross", 1)
        time.sleep(5)
        self.lcd.clear()  # Clear the display after 5 seconds

    def display_emergency_message(self, direction):
        """Display an emergency message on the LCD for 5 seconds."""
        self.lcd.clear()
        self.lcd.message(f"Emergency vehicle", 1)
        time.sleep(5)  # Keep the message for 5 seconds
        self.lcd.clear()  # Clear the display after 5 seconds

    def background(self):
        """Periodically register to the resource catalog."""
        while True:
            self.register()
            time.sleep(10)

    def register(self):
        """Register periodically to the resource catalog to confirm activity."""
        request_string = f'http://{self.resource_catalog_info["ip_address"]}:{self.resource_catalog_info["ip_port"]}/registerResource'
        data = json.load(open(self.led_manager_info))
        try:
            r = requests.put(request_string, json.dumps(data, indent=4))
            print(f'Response: {r.text}')
        except:
            print("An error occurred during registration")


if __name__ == '__main__':
    # Path to the LED manager info and resource catalog info
    script_dir = os.path.dirname(os.path.abspath(__file__))  # Get the directory of the current script
    parent_dir = os.path.dirname(script_dir) 
    parent_dir1 = os.path.dirname(parent_dir)
    led_manager_info_path = os.path.join(script_dir, 'LCD_info.json')
    resource_catalog_info_path = os.path.join(parent_dir1, 'resource_catalog', 'resource_catalog_info.json')

    # Create the LCDSubscriber instance and start the threads
    lcd_subscriber = LCDSubscriber(led_manager_info_path, resource_catalog_info_path)

    # Start the MQTT client and subscribe to topics
    lcd_subscriber.start()

    try:
        while True:
            time.sleep(1)  # Keep the script running and listening for messages

    except KeyboardInterrupt:
        print("\nStopping LCD MQTT Subscriber...")
        lcd_subscriber.stop()
        print("Stopped.")
