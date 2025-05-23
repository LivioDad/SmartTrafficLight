import os
import json
import sqlite3
from shutil import copyfile

DB_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "database", "database.db"))
TEMPLATE_PY = os.path.join(os.path.dirname(__file__), "template_semaphore.py")

SERVICES = ["lcd", "pedestrian", "vulnerable", "ice_warning", "violation_detection", "emergency"]

def get_next_id():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO semaphores (zone, services_enabled) VALUES (?, ?)", ("temp", "{}"))
        new_id = cursor.lastrowid
        conn.commit()
    return new_id

def update_db_entry(new_id, zone, services_dict):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE semaphores SET zone=?, services_enabled=? WHERE id=?", (zone, json.dumps(services_dict), new_id))
        conn.commit()

def main():
    print("=== Add New Semaphore ===")
    zone = input("Enter zone (e.g., A, B, C): ").strip()

    print("Select active services (y/n):")
    services_enabled = {}
    for service in SERVICES:
        answer = input(f" - {service}? (y/n): ").strip().lower()
        services_enabled[service] = (answer == "y")

    new_id = get_next_id()
    update_db_entry(new_id, zone, services_enabled)

    json_path = os.path.join(os.path.dirname(__file__), f"Semaphore_{new_id}_info.json")
    py_path = os.path.join(os.path.dirname(__file__), f"Semaphore_{new_id}.py")
    copyfile(TEMPLATE_PY, py_path)

    json_data = {
        "LedInfo": {
            "ID": f"{zone}_led_{new_id}",
            "Name": f"TrafficLight_{new_id}",
            "Type": "LED_LCD",
            "zone": zone,
            "observed_direction": "NS",
            "availableServices": ["MQTT"],
            "services_enabled": services_enabled,
            "servicesDetails": [{
                "serviceType": "MQTT",
                "topic": f"SmartTrafficLight/Led/{zone}/#",
                "topic_emergency": "SmartTrafficLight/Emergency",
                "topic_ice_warning": f"SmartTrafficLight/LCD/{zone}/roadIcePredictor",
                "topic_status": f"SmartTrafficLight/LightStatus/{zone}_led_{new_id}"
            }],
            "standard_duty_cycle": 5,
            "emergency_duty_cycle": 15,
            "pedestrian_duty_cycle": 7,
            "vulnerable_road_users_duty_cycle": 9,
            "pins": {
                "NS_green": 0,
                "NS_red": 0,
                "WE_green": 0,
                "WE_red": 0,
                "ice_warning": 0
            },
            "last_status": {
                "timestamp": 0,
                "intersection": zone,
                "NS": "red_light",
                "WE": "red_light"
            }
        }
    }

    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)

    print(f"Semaphore {new_id} created in zone '{zone}'.")
    print(f"→ Edit file '{json_path}' to set actual GPIO pins and duty cycles.")

if __name__ == "__main__":
    main()
