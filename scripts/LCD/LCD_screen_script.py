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

        # Initialize the LCD
        self.lcd = LCD(2, 0x27, True)

        # Stato attuale delle righe dell'LCD
        self.line1_text = ""  # Per i warning
        self.line2_text = ""  # Per il countdown

        self.update_display("Waiting for", "sensor data...")

    def centered_message(self, text, line):
        """Centra il testo su una riga dell'LCD"""
        lcd_width = 16
        text = text.center(lcd_width)
        self.lcd.message(text, line)

    def update_display(self, line1=None, line2=None):
        """
        Aggiorna solo le righe modificate dell'LCD per evitare flickering.
        - line1: Testo da mostrare sulla riga 1 (warning)
        - line2: Testo da mostrare sulla riga 2 (countdown)
        """
        if line1 is not None and line1 != self.line1_text:
            self.line1_text = line1
            self.centered_message(line1, 1)
        
        if line2 is not None and line2 != self.line2_text:
            self.line2_text = line2
            self.centered_message(line2, 2)

    def notify(self, topic, payload):
        """Callback triggered when an MQTT message is received."""
        try:
            message_received = json.loads(payload)

            # Countdown fase verde
            if "e" in message_received and message_received["e"]["n"] == "green_light":
                if message_received["e"]["v"] == "NS":
                    remaining = message_received["e"]["c"]
                    self.update_display(line2=f"Red in {remaining}s")
                return

            # Countdown fase rossa
            if "e" in message_received and message_received["e"]["n"] == "red_light":
                if message_received["e"]["v"] == "NS":
                    remaining = message_received["e"]["c"]
                    self.update_display(line2=f"Green in {remaining}s")
                return

            # Countdown emergenza
            if "e" in message_received and message_received["e"]["n"] == "emergency_light":
                remaining = message_received["e"]["c"]
                self.update_display(line1="EMERG VEHICLE!", line2=f"Clear in {remaining}s")
                return

            # Controllo se il messaggio riguarda un warning
            if "e" in message_received and "n" in message_received["e"]:
                warning_type = message_received["e"]["n"]
                print(f"⚠ Detected event: {warning_type}")  # Debugging

            if warning_type == "vul_button":  # Vulnerable user
                self.update_display(line1="VULNERABLE USER!")
                time.sleep(10)
                self.update_display(line1="")
                return

            if warning_type == "ped_sens":  # Pedestrian crossing
                self.update_display(line1="PEDESTRIAN CROSS!")
                time.sleep(10)
                self.update_display(line1="")
                return

        except Exception as e:
            print(f"⚠ Error processing message: {e}")

    def display_vulnerable_user(self):
        """Mostra il messaggio per l'utente vulnerabile sulla riga 1."""
        self.update_display(line1="Vulnerable user")
        time.sleep(10)
        self.update_display(line1="")

    def display_crossing_user(self):
        """Mostra il messaggio per il pedone sulla riga 1."""
        self.update_display(line1="Pedestrian cross")
        time.sleep(10)
        self.update_display(line1="")

    def display_emergency_message(self, direction):
        """Mostra il messaggio di emergenza sulla riga 1."""
        self.update_display(line1="Emerg vehicle!")
        time.sleep(15)
        self.update_display(line1="")

    def start(self):
        """Start MQTT client and subscribe to topics."""
        self.client.start()
        time.sleep(3)  # Allow time for the client to connect
        self.client.mySubscribe("SmartTrafficLight/Sensor/A/#")
        self.client.mySubscribe("SmartTrafficLight/Emergency")
        self.client.mySubscribe("SmartTrafficLight/redLight/A_led_1")
        self.client.mySubscribe("SmartTrafficLight/greenLight/A_led_1")

    def stop(self):
        """Stop the MQTT client and unsubscribe from topics."""
        self.client.unsubscribe()
        time.sleep(3)
        self.client.stop()

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
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    parent_dir1 = os.path.dirname(parent_dir)
    led_manager_info_path = os.path.join(script_dir, 'LCD_info.json')
    resource_catalog_info_path = os.path.join(parent_dir1, 'resource_catalog', 'resource_catalog_info.json')

    lcd_subscriber = LCDSubscriber(led_manager_info_path, resource_catalog_info_path)
    lcd_subscriber.start()

    try:
        while True:
            time.sleep(1)  # Keep the script running

    except KeyboardInterrupt:
        print("\nStopping LCD MQTT Subscriber...")
        lcd_subscriber.stop()
        print("Stopped.")