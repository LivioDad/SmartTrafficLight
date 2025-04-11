import json
import random
import string
import requests
import threading
import time
import os
from MyMQTT import MyMQTT


class ViolationDetector:
    def __init__(self, client_id, mqtt_broker, mqtt_port, mqtt_topic,
                 resource_info_path, resource_catalog_info_path):

        # MQTT setup
        self.client_id = client_id
        self.mqtt_topic = mqtt_topic
        self.mqtt_client = MyMQTT(client_id, mqtt_broker, mqtt_port, self)

        # Load resource info
        with open(resource_info_path) as f:
            self.resource_info = json.load(f)

        # Load catalog info
        with open(resource_catalog_info_path) as f:
            self.resource_catalog_info = json.load(f)

        self.catalog_ip = self.resource_catalog_info["ip_address"]
        self.catalog_port = self.resource_catalog_info["ip_port"]
        self.catalog_register_url = f"http://{self.catalog_ip}:{self.catalog_port}/registerResource"

    def start(self):
        """Start MQTT client and subscribe to topic"""
        self.mqtt_client.start()
        time.sleep(1)
        self.mqtt_client.mySubscribe(self.mqtt_topic)

    def stop(self):
        self.mqtt_client.stop()

    def notify(self, topic, payload):
        """Callback when a message is received via MQTT"""
        try:
            payload = json.loads(payload.decode())
            print(f"Message received on topic '{topic}': {payload}")

            timestamp = payload.get("timestamp")
            station = payload.get("station")

            if not timestamp or station is None:
                print("Invalid message format: missing 'timestamp' or 'station'")
                return

            plate = self.generate_random_plate()
            violation_data = {
                "plate": plate,
                "date": timestamp,
                "station": station
            }

            self.send_violation_to_db(violation_data)

        except Exception as e:
            print(f"Error in notify(): {e}")

    def generate_random_plate(self):
        """Generate a fake license plate"""
        letters = lambda: ''.join(random.choices(string.ascii_uppercase, k=2))
        numbers = lambda: ''.join(random.choices(string.digits, k=3))
        return f"{letters()}{numbers()}{letters()}"

    def get_db_adaptor_url(self):
        """Retrieve DB Adaptor REST URL from service catalog"""
        try:
            url = f"http://{self.catalog_ip}:{self.catalog_port}/resourceID?ID=db_connector_1"
            response = requests.get(url)

            if response.status_code == 200:
                service_info = response.json()
                for service in service_info.get("servicesDetails", []):
                    if service.get("serviceType") == "REST":
                        endpoint = service["endpoint"]
                        print(f"📡 DB Adaptor discovered: {endpoint}")
                        return endpoint
            else:
                print(f"Failed to retrieve db adaptor info: HTTP {response.status_code}")
        except Exception as e:
            print(f"Error discovering DB adaptor: {e}")
        return None

    def send_violation_to_db(self, data):
        """Send a new violation to the DB Adaptor"""
        db_url = self.get_db_adaptor_url()
        if not db_url:
            print("Cannot send violation: DB adaptor not available.")
            return

        try:
            response = requests.post(db_url, json=data)
            if response.status_code == 201:
                print(f"Violation registered: {data}")
            else:
                print(f"Failed to register violation: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error sending POST to DB adaptor: {e}")

    def register_to_catalog(self):
        """Register periodically to the Service Catalog"""
        while True:
            try:
                self.resource_info["lastUpdate"] = time.time()
                response = requests.put(self.catalog_register_url, json=self.resource_info)
                print(f"Registered to catalog: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"Catalog registration failed: {e}")
            time.sleep(10)

    def run(self):
        """Launch MQTT + registration in background threads"""
        threading.Thread(target=self.register_to_catalog, name="register_thread", daemon=True).start()
        threading.Thread(target=self.start, name="mqtt_thread", daemon=True).start()

if __name__ == "__main__":
    import os

    # Dynamically determine base path
    base_path = os.path.dirname(os.path.abspath(__file__))


    # File paths
    
    info_path = os.path.join(base_path, "violation_detection_info.json")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    resource_catalog_path = os.path.join(script_dir, "..", "resource_catalog", "resource_catalog_info.json")
    resource_catalog_path = os.path.normpath(resource_catalog_path)

    # Load config list from JSON
    with open(info_path, "r") as f:
        info_data = json.load(f)

    config = info_data["config"][0]

    # Initialize and run detector
    detector = ViolationDetector(
        client_id=config["client_id"],
        mqtt_broker=config["mqtt_broker"],
        mqtt_port=config["mqtt_port"],
        mqtt_topic=config["mqtt_topic"],
        resource_info_path=info_path,
        resource_catalog_info_path=resource_catalog_path
    )

    detector.run()

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("Stopping detector...")
        detector.stop()
