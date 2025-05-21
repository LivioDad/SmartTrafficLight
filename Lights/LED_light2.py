from MyMQTT import *
import time
import json
import requests
from gpiozero import LED
import threading
import os

# On LED2 only the emergency mode is implemented and no LCD is configured, as an example
# of a simple traffic light without LCD, buttons or pedestrian presence sensors

class LEDLights:
    def __init__(self, led_info, resource_catalog_file):
        # Retrieve broker info from the resource catalog
        self.resource_catalog = json.load(open(resource_catalog_file))
        request_string = 'http://' + self.resource_catalog["ip_address"] + ':' + self.resource_catalog["ip_port"] + '/broker'
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["name"]
        self.port = rjson["port"]

        # Load LED configuration
        led_info = led_info["LedInfo"]
        self.led_info = led_info
        self.topic = led_info["servicesDetails"][0]["topic"]
        self.topic_emergency = led_info["servicesDetails"][0]["topic_emergency"]

        self.clientID = led_info["Name"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, self)

        # Load duty cycles
        self.standard_cycle = led_info["standard_duty_cycle"]
        self.vulnerable_cycle = led_info["vulnerable_road_users_duty_cycle"]
        self.pedestrian_cycle = led_info["pedestrian_duty_cycle"]
        self.emergency_cycle = led_info["emergency_duty_cycle"]

        self.intersection_number = led_info["ID"].split('_')[2]
        self.zone = led_info["zone"]
        self.pins = led_info["pins"]

        # Initialize LED lights
        self.NS_green = LED(self.pins["NS_green"])
        self.NS_red = LED(self.pins["NS_red"])
        self.WE_green = LED(self.pins["WE_green"])
        self.WE_red = LED(self.pins["WE_red"])

        # Cycle management:
        self.cycle_lock = threading.Lock()
        self.active_mode = "standard"
        self.active_duration = self.standard_cycle
        self.active_direction = None

        # pending_* keeps in memory the command that will be applied at the end of the current cycle
        self.pending_mode = None
        self.pending_duration = None
        self.pending_direction = None
        
        # Starts main cycle in a separate thread
        self.running = True
        threading.Thread(target=self.main_cycle).start()

    def register(self):
        """ Periodically registers the LED system to the resource catalog. """
        request_string = 'http://' + self.resource_catalog["ip_address"] + ':' + self.resource_catalog["ip_port"] + '/registerResource'
        data = self.led_info
        try:
            r = requests.put(request_string, json.dumps(data, indent=4))
            print(f'Response: {r.text}')
        except:
            print("An error occurred during registration")

    def start(self):
        """ Starts the MQTT client and subscribes to topics. """
        self.client.start()
        time.sleep(3)
        self.client.mySubscribe(self.topic)
        self.client.mySubscribe(self.topic_emergency)

    def stop(self):
        """ Unsubscribes and stops the MQTT client. """
        self.client.unsubscribe()
        time.sleep(3)
        self.client.stop()

    def notify(self, topic, payload):
        payload = json.loads(payload)
        print(f"[MQTT RECEIVED] Topic: {topic}, Payload: {payload}")

        new_mode = None
        new_duration = None
        new_direction = None

        # Standard emergency message management
        if topic == self.topic_emergency and payload.get("zone") == self.zone:
            new_mode = "emergency"
            new_duration = self.emergency_cycle
            new_direction = payload.get("direction")
            print(f"[EMERGENCY] From manager: zone={self.zone}, direction={new_direction}")

        # Direct message management (double publish from emergency sim)
        elif "e" in payload and isinstance(payload["e"], dict):
            e = payload["e"]
            if e.get("v") == "emergency" and e.get("zone") == self.zone:
                new_mode = "emergency"
                new_duration = self.emergency_cycle
                new_direction = e.get("direction")
                print(f"[EMERGENCY] Direct: zone={self.zone}, direction={new_direction}")

        if new_mode == "emergency":
            with self.cycle_lock:
                if self.active_mode != "emergency" and self.pending_mode != "emergency":
                    self.pending_mode = new_mode
                    self.pending_duration = new_duration
                    self.pending_direction = new_direction
                    print("[INFO] Emergency cycle scheduled.")
                else:
                    print("[INFO] Emergency already active or pending. Ignored.")

    def main_cycle(self):
        """
        Main loop that executes an entire iteration (two-phase loop) based on the active mode.
        At the end of the iteration, if there is a pending command, it is applied.
        """
        while self.running:
            with self.cycle_lock:
                mode = self.active_mode
                duration = self.active_duration
                direction = self.active_direction

            if mode == "emergency":
                self.run_emergency_cycle(duration, direction)
            else:
                self.run_standard_cycle(duration, mode)

            # At the end of the cycle, apply the pending command if present
            with self.cycle_lock:
                if self.pending_mode is not None:
                    self.active_mode = self.pending_mode
                    self.active_duration = self.pending_duration
                    self.active_direction = self.pending_direction
                    self.pending_mode = None
                    self.pending_duration = None
                    self.pending_direction = None
                    print("Cycle updated to:", self.active_mode)
                else:
                    # If there is no pending command, it returns to standard mode
                    self.active_mode = "standard"
                    self.active_duration = self.standard_cycle
                    self.active_direction = None

    def run_standard_cycle(self, duration, mode):
        """
        Performs a standard (two-phase) cycle for the specified mode.
        The mode can be "standard", "vulnerable", or "pedestrian".
        """
        print(f"Running {mode} cycle for {duration} seconds per phase.")
        # Phase 1: NS green, WE red
        self.NS_green.on()
        self.NS_red.off()
        self.WE_green.off()
        self.WE_red.on()
        time.sleep(duration)

        # Phase 2: NS red, WE green
        self.NS_green.off()
        self.NS_red.on()
        self.WE_green.on()
        self.WE_red.off()
        time.sleep(duration)

    def run_emergency_cycle(self, duration, direction):
        """
        Runs the emergency cycle for the specified duration and direction.
        During the emergency, any standard updates are ignored.
        """
        print("EMERGENCY ACTIVATED. Duration:", duration, "Direction:", direction)
        # Turn off all LEDs to reset the state
        self.NS_green.off()
        self.NS_red.off()
        self.WE_green.off()
        self.WE_red.off()

        if direction == 'NS':
            self.NS_green.on()
            self.WE_red.on()
        elif direction == 'WE':
            self.WE_green.on()
            self.NS_red.on()
        else:
            print("Direction not specified, defaulting to standard emergency configuration.")
        
        time.sleep(duration)

        # After the emergency ends, it returns to standard mode
        with self.cycle_lock:
            self.active_mode = "standard"
            self.active_duration = self.standard_cycle
            self.active_direction = None
            self.pending_mode = None
            self.pending_duration = None
            self.pending_direction = None

    def background(self):
        """ Periodically registers the LED system every 10 seconds. """
        while True:
            self.register()
            time.sleep(10)

    def foreground(self):
        """ Starts the MQTT client and listens for messages. """
        self.start()


if __name__ == '__main__':
    # Load JSON configuration files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    #resource_catalog_path = os.path.join(os.path.dirname(script_dir), "resource_catalog", "resource_catalog_info.json")
    resource_catalog_path = os.path.join(script_dir, 'resource_catalog_info.json')
    led_info_path = os.path.join(script_dir, "LED_light2_info.json")

    info = json.load(open(led_info_path))

    led = LEDLights(info, resource_catalog_path)

    # Start background and foreground threads
    threading.Thread(name='background', target=led.background).start()
    threading.Thread(name='foreground', target=led.foreground).start()

    while True:
        time.sleep(0.5)