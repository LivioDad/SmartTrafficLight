import os
import json
import time
import threading
import requests
from gpiozero import LED
from MyMQTT import MyMQTT

try:
    from LCD_config import LCD
except ImportError:
    LCD = None

PRIORITY = {
    "standard": 0,
    "pedestrian": 1,
    "vulnerable": 2,
    "emergency": 3
}

class Semaphore:
    def __init__(self, led_info_path, resource_catalog_path):
        self.led_info_path = led_info_path
        self.resource_catalog = json.load(open(resource_catalog_path))
        self.led_info_data = json.load(open(led_info_path))
        led_info = self.led_info_data["LedInfo"]
        self.led_info = led_info
        self.services_enabled = led_info.get("services_enabled", {})

        self.clientID = led_info["Name"]
        self.zone = led_info["zone"]
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
        self.ice_warning_led = LED(led_info["pins"]["ice_warning"]) if self.services_enabled.get("ice_warning") else None
        self.lcd = LCD(2, 0x27, True) if self.services_enabled.get("lcd") and LCD else None

        broker_info = requests.get(f"http://{self.resource_catalog['ip_address']}:{self.resource_catalog['ip_port']}/broker").json()
        self.client = MyMQTT(self.clientID, broker_info["name"], broker_info["port"], self)

        self.current_mode = "standard"
        self.current_direction = None
        self.current_duration = self.standard_cycle
        self.pending = None
        self.emergency_queue = []

    def start(self):
        self.client.start()
        time.sleep(2)
        self.client.mySubscribe(self.topic)
        if self.services_enabled.get("emergency"):
            self.client.mySubscribe(self.topic_emergency)
        if self.services_enabled.get("ice_warning"):
            self.client.mySubscribe(self.topic_ice_warning)

    def notify(self, topic, payload):
        payload = json.loads(payload)
        print(f"[MQTT RECEIVED] Topic: {topic}, Payload: {payload}")

        if topic == self.topic_emergency and self.services_enabled.get("emergency") and payload["zone"] == self.zone:
            self.emergency_queue.append({
                "mode": "emergency",
                "priority": PRIORITY["emergency"],
                "duration": self.emergency_cycle,
                "direction": payload["direction"],
                "warning": "EMERG VEHICLE!"
            })

        elif topic.startswith(self.topic.rstrip('#')):
            if "e" in payload and isinstance(payload["e"], dict):
                cmd = payload["e"]["v"]
                if cmd == "pedestrian" and self.services_enabled.get("pedestrian"):
                    self.try_set_pending("pedestrian", self.pedestrian_cycle, "PEDESTRIAN CROSS!")
                elif cmd == "vulnerable_pedestrian" and self.services_enabled.get("vulnerable"):
                    self.try_set_pending("vulnerable", self.vulnerable_cycle, "VULNERABLE USER!")

        elif topic == self.topic_ice_warning and self.services_enabled.get("ice_warning"):
            for entry in payload.get("e", []):
                if entry["n"] == "ice_risk" and entry["v"] > 0.5:
                    self.try_set_pending("vulnerable", self.vulnerable_cycle, "ICE WARNING!")
                    if self.ice_warning_led:
                        self.ice_warning_led.on()
                        threading.Thread(target=self.turn_off_ice_led_after_delay, daemon=True).start()

    def turn_off_ice_led_after_delay(self):
        time.sleep(30)
        if self.ice_warning_led:
            self.ice_warning_led.off()

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
            if self.lcd:
                self.lcd.message(warning.center(16), 1)

    def update_status_json(self):
        status = {
            "timestamp": time.time(),
            "intersection": self.zone,
            "NS": "green_light" if self.NS_green.value else "red_light",
            "WE": "green_light" if self.WE_green.value else "red_light"
        }
        self.led_info_data["LedInfo"]["last_status"] = status
        try:
            with open(self.led_info_path, "w") as f:
                json.dump(self.led_info_data, f, indent=2)
        except Exception as e:
            print(f"[WRITE ERROR] Failed to update status in JSON: {e}")

    def countdown(self, template, duration):
        for remaining in range(duration, 0, -1):
            if self.lcd:
                self.lcd.message(template.format(remaining).center(16), 2)
            time.sleep(1)
        if self.lcd:
            self.lcd.message(" ".center(16), 2)

    def run_cycle(self, mode, duration, direction=None, warning=""):
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
            if self.lcd:
                self.lcd.message(warning.center(16), 1)
            self.update_status_json()
            self.countdown("Clear in {}s", duration)
        else:
            if self.lcd:
                self.lcd.message(warning.center(16) if warning else " ".center(16), 1)
            self.NS_green.on()
            self.NS_red.off()
            self.WE_green.off()
            self.WE_red.on()
            self.update_status_json()
            self.countdown("Green in {}s" if self.observed_direction == "WE" else "Red in {}s", duration)
            self.NS_green.off()
            self.NS_red.on()
            self.WE_green.on()
            self.WE_red.off()
            self.update_status_json()
            self.countdown("Green in {}s" if self.observed_direction == "NS" else "Red in {}s", duration)
        if self.lcd:
            self.lcd.message(" ".center(16), 1)
            self.lcd.message(" ".center(16), 2)

    def run(self):
        self.start()
        last_mode = None
        while True:
            if self.emergency_queue:
                job = self.emergency_queue.pop(0)
                last_mode = None
            elif self.pending:
                if self.pending["mode"] == last_mode:
                    job = {"mode": "standard", "priority": PRIORITY["standard"], "duration": self.standard_cycle}
                    last_mode = "standard"
                else:
                    job = self.pending
                    last_mode = job["mode"]
                    self.pending = None
            else:
                job = {"mode": "standard", "priority": PRIORITY["standard"], "duration": self.standard_cycle}
                last_mode = "standard"
            self.run_cycle(job["mode"], job["duration"], job.get("direction"), job.get("warning", ""))


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    resource_catalog_path = os.path.join(os.path.dirname(script_dir), "resource_catalog_info.json")
    led_info_path = os.path.join(script_dir, "Semaphore_2_info.json")
    system = Semaphore(led_info_path, resource_catalog_path)
    threading.Thread(target=system.run, daemon=True).start()
    while True:
        time.sleep(1)