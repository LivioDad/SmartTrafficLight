import os
import json
import time
from gpiozero import LED
from LCD_config import LCD
from MyMQTT import MyMQTT
import requests
import threading

# This script controls the LED and LCD display for a traffic light system.
# It subscribes to MQTT topics for emergency and pedestrian signals, and manages the light cycles accordingly.
# It writes continuously the status of the traffic light to a JSON file, to allow the infraction sensor script to read it with few latency

PRIORITY = {
    "standard": 0,
    "pedestrian": 1,
    "vulnerable": 2,
    "emergency": 3
}

class LED_LCD:
    def __init__(self, led_info_path, resource_catalog_path):
        # Load configuration
        self.resource_catalog = json.load(open(resource_catalog_path))
        self.status_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "light1_status.json")
        led_info = json.load(open(led_info_path))["LedInfo"]
        self.led_info = led_info

        self.clientID = led_info["Name"]
        self.zone = led_info["zone"]
        self.intersection_number = led_info["ID"].split('_')[2]
        self.topic = led_info["servicesDetails"][0]["topic"]
        self.topic_emergency = led_info["servicesDetails"][0]["topic_emergency"]
        self.topic_ice_warning = led_info["servicesDetails"][0]["topic_ice_warning"]
        self.observed_direction = led_info.get("observed_direction", "NS")

        self.standard_cycle = led_info["standard_duty_cycle"]
        self.vulnerable_cycle = led_info["vulnerable_road_users_duty_cycle"]
        self.pedestrian_cycle = led_info["pedestrian_duty_cycle"]
        self.emergency_cycle = led_info["emergency_duty_cycle"]

        self.NS_green = LED(led_info["pins"]["NS_green"])
        self.NS_red = LED(led_info["pins"]["NS_red"])
        self.WE_green = LED(led_info["pins"]["WE_green"])
        self.WE_red = LED(led_info["pins"]["WE_red"])
        self.ice_warning_led = LED(led_info["pins"]["ice_warning"]) 

        self.lcd = LCD(2, 0x27, True)

        broker_info = requests.get(f"http://{self.resource_catalog['ip_address']}:{self.resource_catalog['ip_port']}/broker").json()
        self.broker = broker_info["name"]
        self.port = broker_info["port"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, self)

        self.current_mode = "standard"
        self.current_direction = None
        self.current_duration = self.standard_cycle
        self.pending = None
        self.emergency_queue = []

    def start(self):
        self.client.start()
        time.sleep(2)
        self.client.mySubscribe(self.topic)
        self.client.mySubscribe(self.topic_emergency)
        self.client.mySubscribe(self.topic_ice_warning)

    def notify(self, topic, payload):
        payload = json.loads(payload)
        print(f"[MQTT RECEIVED] Topic: {topic}, Payload: {payload}")

        if topic == self.topic_emergency and payload["zone"] == self.zone:
            print("[INFO] Emergency command received")
            self.emergency_queue.append({
                "mode": "emergency",
                "priority": PRIORITY["emergency"],
                "duration": self.emergency_cycle,
                "direction": payload["direction"],
                "warning": "EMERG VEHICLE!"
            })

        elif topic.startswith(self.topic.rstrip('#')):      # <— match with wildcard
            if "e" in payload and isinstance(payload["e"], dict):
                cmd = payload["e"]["v"]
                if cmd == "pedestrian":
                    self.try_set_pending("pedestrian",
                                        self.pedestrian_cycle,
                                        "PEDESTRIAN CROSS!")
                elif cmd == "vulnerable_pedestrian":
                    self.try_set_pending("vulnerable",
                                        self.vulnerable_cycle,
                                        "VULNERABLE USER!")


        elif topic == self.topic_ice_warning:
            if "e" in payload:
                for entry in payload["e"]:
                    if entry["n"] == "ice_risk" and entry["v"] > 0.5:
                        warning_msg = "ICE WARNING!"
                        print(f"[WARNING] Ice risk detected: {entry['v']}")
                        self.try_set_pending("vulnerable", self.vulnerable_cycle, warning_msg)

                        self.ice_warning_led.on()
                        threading.Thread(target=self.turn_off_ice_led_after_delay, daemon=True).start()

    def turn_off_ice_led_after_delay(self):
        time.sleep(30)
        self.ice_warning_led.off()
                    
    def write_status_to_file(self):
        status_data = {
            "timestamp": time.time(),
            "intersection": self.zone,
            "NS": "green_light" if self.NS_green.value else "red_light",
            "WE": "green_light" if self.WE_green.value else "red_light"
        }
        try:
            with open(self.status_file_path, "w") as f:
                json.dump(status_data, f)
        except Exception as e:
            print(f"[FILE WRITE ERROR] {e}")

    def try_set_pending(self, mode, duration, warning):
        priority = PRIORITY[mode]
        if self.pending is None or priority > self.pending["priority"]:
            self.pending = {
                "mode": mode,
                "priority": priority,
                "duration": duration,
                "direction": None,
                "warning": warning
            }
            print(f"[INFO] Set pending mode: {mode.upper()} ({duration}s)")
            self.update_display(line1=warning)
        else:
            print(f"[INFO] Ignored {mode} command due to lower priority or duplicate")

    def update_display(self, line1=None, line2=None):
        if line1 is not None:
            self.lcd.message(line1.center(16), 1)
        if line2 is not None:
            self.lcd.message(line2.center(16), 2)

    def countdown(self, template, duration):
        for remaining in range(duration, 0, -1):
            self.update_display(line2=template.format(remaining))
            time.sleep(1)
        self.update_display(line2="")

    def run_cycle(self, mode, duration, direction=None, warning=""):
        print(f"Running cycle: {mode.upper()} ({duration}s)")

        if mode == "emergency":
            self.NS_green.off()
            self.NS_red.off()
            self.WE_green.off()
            self.WE_red.off()

            if direction == "NS":
                self.NS_green.on()
                self.WE_red.on()
            elif direction == "WE":
                self.WE_green.on()
                self.NS_red.on()

            self.write_status_to_file()
            self.update_display(line1=warning)
            self.countdown("Clear in {}s", duration)

        else:
            self.update_display(line1=warning if mode != "standard" else "")

            # Phase 1 – Green on NS
            self.NS_green.on()
            self.NS_red.off()
            self.WE_red.on()
            self.WE_green.off()
            self.write_status_to_file()
            if self.observed_direction == "WE":
                self.countdown("Green in {}s", duration)
            else:
                self.countdown("Red in {}s", duration)

            # Phase 2 – Green on WE
            self.NS_green.off()
            self.NS_red.on()
            self.WE_red.off()
            self.WE_green.on()
            self.write_status_to_file()
            if self.observed_direction == "NS":
                self.countdown("Green in {}s", duration)
            else:
                self.countdown("Red in {}s", duration)

        self.update_display(line1="", line2="")

    def run(self):
        self.start()
        print("System started.")
        last_executed_mode = None

        while True:
            # Priority 1: Emergency
            if self.emergency_queue:
                job = self.emergency_queue.pop(0)
                last_executed_mode = None  # forziamo l'esecuzione
            # Priority 2: pending mode (pedestrian, vulnerable, etc.)
            elif self.pending is not None:
                # If it is the same as the last executed and is not emergency --> ignore 
                # (at least a standard cycle between two particular modes)
                if self.pending["mode"] == last_executed_mode and \
                self.pending["priority"] == PRIORITY.get(last_executed_mode, 0):
                    print(f"[INFO] Ignored pending mode '{self.pending['mode']}' (already executed)")
                    self.pending = None
                    job = {
                        "mode": "standard",
                        "priority": PRIORITY["standard"],
                        "duration": self.standard_cycle,
                        "direction": None,
                        "warning": ""
                    }
                    last_executed_mode = "standard"
                else:
                    job = self.pending
                    last_executed_mode = job["mode"]
                    self.pending = None
            # If no pending mode, run standard cycle
            else:
                job = {
                    "mode": "standard",
                    "priority": PRIORITY["standard"],
                    "duration": self.standard_cycle,
                    "direction": None,
                    "warning": ""
                }
                last_executed_mode = "standard"

            self.current_mode = job["mode"]
            self.current_duration = job["duration"]
            self.current_direction = job["direction"]

            print(f"[RUNNING] Cycle: {self.current_mode.upper()} ({self.current_duration}s)")
            self.run_cycle(job["mode"], job["duration"], job["direction"], job["warning"])

    def register(self):
        request_string = f"http://{self.resource_catalog['ip_address']}:{self.resource_catalog['ip_port']}/registerResource"
        try:
            r = requests.put(request_string, json.dumps(self.led_info, indent=4))
            print(f"[REGISTER] Response: {r.text}")
        except Exception as e:
            print(f"[REGISTER ERROR] {e}")

    def background_registration(self):
        while True:
            self.register()
            time.sleep(10)


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    resource_catalog_path = os.path.join(os.path.dirname(script_dir), "resource_catalog_info.json")
    led_info_path = os.path.join(script_dir, "LED_LCD_info1.json")

    system = LED_LCD(led_info_path, resource_catalog_path)

    # Start a thread for the registration to the catalog
    threading.Thread(target=system.background_registration, daemon=True).start()
    # Start the main loop
    system.run()