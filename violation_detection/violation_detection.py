import json
import random
import string
import requests
import threading
import time
from MyMQTT import MyMQTT


class ViolationDetector:
    def __init__(self, client_id, mqtt_broker, mqtt_port, mqtt_topic,
                 resource_info_path, resource_catalog_info_path):

        # MQTT
        self.client_id = client_id
        self.mqtt_topic = mqtt_topic
        self.mqtt_client = MyMQTT(client_id, mqtt_broker, mqtt_port, self)

        # Catalog info
        self.resource_info_path = resource_info_path
        self.resource_info = json.load(open(resource_info_path))
        self.resource_catalog_info = json.load(open(resource_catalog_info_path))
        self.catalog_ip = self.resource_catalog_info["ip_address"]
        self.catalog_port = self.resource_catalog_info["ip_port"]
        self.catalog_register_url = f"http://{self.catalog_ip}:{self.catalog_port}/registerResource"

    def start(self):
        """Start MQTT client and subscribe to topic"""
        self.mqtt_client.start()
        time.sleep(2)
        self.mqtt_client.mySubscribe(self.mqtt_topic)

    def stop(self):
        self.mqtt_client.stop()

    def notify(self, topic, payload):
        """Callback on MQTT message"""
        try:
            payload = json.loads(payload.decode())
            print(f"📩 Message received on topic '{topic}': {payload}")

            timestamp = payload.get("timestamp")
            station = payload.get("station")

            if not timestamp or station is None:
                print("⚠️ Invalid message format: missing 'timestamp' or 'station'")
                return

            plate = self.generate_random_plate()

            violation_data = {
                "plate": plate,
                "date": timestamp,
                "station": station
            }

            self.send_violation_to_db(violation_data)

        except Exception as e:
            print(f"❌ Error in notify(): {e}")

    def generate_random_plate(self):
        """Generate a fake license plate"""
        letters = lambda: ''.join(random.choices(string.ascii_uppercase, k=2))
        numbers = lambda: ''.join(random.choices(string.digits, k=3))
        return f"{letters()}{numbers()}{letters()}"

    def get_db_adaptor_url(self):
        """Discover DB Adaptor REST endpoint from Service Catalog"""
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
                print(f"❌ Failed to retrieve db adaptor info: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ Error discovering DB adaptor: {e}")
        return None

    def send_violation_to_db(self, data):
        """Send violation info to the discovered DB Adaptor"""
        db_url = self.get_db_adaptor_url()
        if not db_url:
            print("⚠️ Cannot send violation: DB adaptor not available.")
            return

        try:
            response = requests.post(db_url, json=data)
            if response.status_code == 201:
                print(f"✅ Violation registered: {data}")
            else:
                print(f"❌ Failed to register violation: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Error sending POST to DB adaptor: {e}")

    def register_to_catalog(self):
        """Register periodically to the service catalog"""
        while True:
            try:
                self.resource_info["lastUpdate"] = time.time()
                response = requests.put(self.catalog_register_url, json=self.resource_info)
                print(f"📡 Registered to catalog: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"❌ Catalog registration failed: {e}")
            time.sleep(10)

    def run(self):
        """Start MQTT and catalog registration in background"""
        threading.Thread(target=self.register_to_catalog, name="register_thread", daemon=True).start()
        threading.Thread(target=self.start, name="mqtt_thread", daemon=True).start()

# config.json: keep local configuration paramethers to start the program
# resource_info_violation_detector.json: describes the service to register into the service catalog
# resource_catalog_info.json: contains information about the service catalog

if __name__ == "__main__":
    import os

    # Dynamically determine the base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Construct paths for configuration files
    config_path = os.path.join(base_dir, "config.json")
    resource_info_path = os.path.join(base_dir, "resource_info_violation_detector.json")
    resource_catalog_info_path = os.path.join(base_dir, "resource_catalog_info.json")

    # Load MQTT and client config
    with open(config_path) as f:
        config = json.load(f)

    detector = ViolationDetector(
        client_id=config["client_id"],
        mqtt_broker=config["mqtt_broker"],
        mqtt_port=config["mqtt_port"],
        mqtt_topic=config["mqtt_topic"],
        resource_info_path=resource_info_path,
        resource_catalog_info_path=resource_catalog_info_path
    )

    detector.run()

    # Keep the main thread alive
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("🛑 Stopping detector...")
        detector.stop()
