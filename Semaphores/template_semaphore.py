import os
import time
import threading
import json
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

    def update_status_json(self):
        status = {
            "timestamp": time.time(),
            "intersection": self.zone,
            "NS": "green_light" if self.NS_green.value else "red_light",
            "WE": "green_light" if self.WE_green.value else "red_light"
        }
        self.led_info_data["LedInfo"]["last_status"] = status
        with open(self.led_info_path, "w") as f:
            json.dump(self.led_info_data, f, indent=2)

    def run(self):
        self.start()
        while True:
            self.NS_green.on()
            self.NS_red.off()
            self.WE_red.on()
            self.WE_green.off()
            self.update_status_json()
            time.sleep(self.standard_cycle)

            self.NS_green.off()
            self.NS_red.on()
            self.WE_red.off()
            self.WE_green.on()
            self.update_status_json()
            time.sleep(self.standard_cycle)

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    resource_catalog_path = os.path.join(os.path.dirname(script_dir), "resource_catalog_info.json")
    led_info_path = os.path.join(script_dir, "Semaphore_X_info.json")
    system = Semaphore(led_info_path, resource_catalog_path)
    threading.Thread(target=system.run, daemon=True).start()
    while True:
        time.sleep(1)
