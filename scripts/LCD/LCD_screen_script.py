import time
import json
from LCD_config import LCD
from MyMQTT import MyMQTT
import requests
import os

""" This script manages an LCD thought to be placed on traffic light A1 in direction NS"""

class LCDSubscriber:
    def __init__(self, led_manager_info, resource_catalog_info):
        # Load the configuration
        self.resource_catalog_info = json.load(open(resource_catalog_info))
        led_info = json.load(open(led_manager_info))

        # Request information from the resource catalog
        request_string = f'http://{self.resource_catalog_info["ip_address"]}:{self.resource_catalog_info["ip_port"]}/broker'
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["name"]
        self.port = rjson["port"]

        # Extract topics from LED manager info
        for s in led_info["serviceDetails"]:
            if s["serviceType"] == 'MQTT':
                self.topicS = s["topic_subscribe"]
                self.topicE = s["topic_emergency"]
                self.topicStatus = s["topic_status"]
                self.topicTransition = s["topic_transition"]
        self.intersection_number = led_info["Name"].split('_')[2]
        
        self.clientID = led_info["Name"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, self)

        # Initialize LCD
        self.lcd = LCD(2, 0x27, True)

        # LCD status
        self.line1_text = ""  # Warning
        self.line2_text = ""  # Countdown

        # Warning control
        self.warning_active = False
        self.warning_end_time = 0  # Time when the warning should disappear

        self.update_display("Waiting for", "sensor data...")

    def centered_message(self, text, line):
        """Centers the text on a line of the LCD"""
        lcd_width = 16
        text = text.center(lcd_width)
        self.lcd.message(text, line)

    def update_display(self, line1=None, line2=None):
        """Updates only the modified lines of the LCD"""
        if line1 is not None and line1 != self.line1_text:
            self.line1_text = line1
            self.centered_message(line1, 1)
        
        if line2 is not None and line2 != self.line2_text:
            self.line2_text = line2
            self.centered_message(line2, 2)

    def notify(self, topic, payload):
        # print(f"Received message on topic {topic}: {payload}")
        """Callback when an MQTT message arrives."""
        try:
            message_received = json.loads(payload)

            # Warning
            if "e" in message_received and "n" in message_received["e"]:
                warning_type = message_received["e"]["n"]

            if warning_type == "vul_button":  # Vulnerable user
                self.show_warning("VULNERABLE USER!")
                return

            if warning_type == "ped_sens":  # Pedestrian
                self.show_warning("PEDESTRIAN CROSS!")
                return

            # Check for standard transition message
            if "e" in message_received and message_received["e"]["n"] == "standard_transition":
                self.update_display(line1="")  # Clear line 1 immediately
                return  

            # Green light countdown
            if "e" in message_received and message_received["e"]["n"] == "green_light":
                if message_received["e"]["v"] == "NS":
                    remaining = message_received["e"]["c"]
                    self.update_display(line2=f"Red in {remaining-1}s")
                return

            # Red light countdown
            if "e" in message_received and message_received["e"]["n"] == "red_light":
                if message_received["e"]["v"] == "NS":
                    remaining = message_received["e"]["c"]
                    self.update_display(line2=f"Green in {remaining-1}s")
                return

            # Dynamic emergency countdown
            if "e" in message_received and message_received["e"]["n"] == "emergency_light" and message_received["e"]["i"] == self.intersection_number:
                remaining = message_received["e"]["c"]
                self.update_display(line1="EMERG VEHICLE!", line2=f"Clear in {remaining}s")
                return

        except Exception as e:
            print(f"⚠ Error processing message: {e}")

    def show_warning(self, message):
        """Displays a warning message on the LCD."""
        self.update_display(line1=message)

    def start(self):
        """Starts the MQTT client and subscribes to the topics."""
        self.client.start()
        time.sleep(3)  # Time for the connection
        self.client.mySubscribe(self.topicS)
        self.client.mySubscribe(self.topicE)
        self.client.mySubscribe(self.topicStatus)
        self.client.mySubscribe(self.topicTransition)
        
    def stop(self):
        """Stops the MQTT client."""
        self.client.unsubscribe()
        time.sleep(3)
        self.client.stop()


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    parent_dir1 = os.path.dirname(parent_dir)
    led_manager_info_path = os.path.join(script_dir, 'LCD_info.json')
    resource_catalog_info_path = os.path.join(parent_dir1, 'resource_catalog', 'resource_catalog_info.json')

    lcd_subscriber = LCDSubscriber(led_manager_info_path, resource_catalog_info_path)
    lcd_subscriber.start()

    try:
        while True:
            time.sleep(1)  # Keeps the program running

    except KeyboardInterrupt:
        print("\nStopping LCD MQTT Subscriber...")
        lcd_subscriber.stop()
        print("Stopped.")