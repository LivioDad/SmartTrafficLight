from MyMQTT import *
import time
import json
import requests
from gpiozero import LED
import threading
import os

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
        self.topic_zone = led_info["servicesDetails"][0]["topic_zone"]
        self.topic_status = led_info["servicesDetails"][0]["topic_status"]
        self.topic_trans = led_info["servicesDetails"][0]["topic_trans"]
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
        # active_mode: "standard", "vulnerable", "pedestrian", "emergency"
        # active_duration: durata per fase del ciclo corrente
        # active_direction: solo per emergency (None altrimenti)
        self.cycle_lock = threading.Lock()
        self.active_mode = "standard"
        self.active_duration = self.standard_cycle
        self.active_direction = None

        # pending_* memorizza il comando che verrà applicato al termine del ciclo corrente
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
            # Debug: print(f'Response: {r.text}')
        except:
            print("An error occurred during registration")

    def start(self):
        """ Starts the MQTT client and subscribes to topics. """
        self.client.start()
        time.sleep(3)
        self.client.mySubscribe(self.topic)
        self.client.mySubscribe(self.topic_zone)
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

        # Gestione messaggi standard di emergenza
        if topic == self.topic_emergency and payload.get("zone") == self.zone:
            new_mode = "emergency"
            new_duration = self.emergency_cycle
            new_direction = payload.get("direction")
            print(f"[EMERGENCY] From manager: zone={self.zone}, direction={new_direction}")

        # Gestione messaggi diretti (doppio publish da emergency_sim)
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
        Ciclo principale che esegue un'intera iterazione (ciclo a due fasi) in base alla modalità attiva.
        Al termine dell'iterazione, se esiste un comando pending, questo viene applicato.
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

            # Al termine del ciclo, applica il comando pending se presente
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
                    # Se non c'è comando pendente, ritorna alla modalità standard
                    self.active_mode = "standard"
                    self.active_duration = self.standard_cycle
                    self.active_direction = None

    def run_standard_cycle(self, duration, mode):
        if duration == self.standard_cycle and self.active_mode == "standard":
            self.publish_standard_transition()
        """
        Esegue un ciclo standard (due fasi) per la modalità specificata.
        La modalità può essere "standard", "vulnerable" o "pedestrian".
        """
        print(f"Running {mode} cycle for {duration} seconds per phase.")
        # Fase 1: NS verde, WE rosso
        self.NS_green.on()
        self.NS_red.off()
        self.WE_green.off()
        self.WE_red.on()
        self.publish_red_light("WE", duration)
        for remaining in range(duration, 0, -1):
            self.publish_green_light("NS", remaining)
            time.sleep(1)

        # Fase 2: NS rosso, WE verde
        self.NS_green.off()
        self.NS_red.on()
        self.WE_green.on()
        self.WE_red.off()
        for remaining in range(duration, 0, -1):
            self.publish_red_light("NS", remaining)
            time.sleep(1)

    def run_emergency_cycle(self, duration, direction):
        """
        Esegue il ciclo di emergenza per la durata specificata e con la direzione indicata.
        Durante l'emergency, eventuali aggiornamenti standard vengono ignorati.
        """
        print("EMERGENCY ACTIVATED. Duration:", duration, "Direction:", direction)
        # Spegne tutti i LED per resettare lo stato
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

        # Countdown per il tempo di emergenza
        for remaining in range(duration, 0, -1):
            self.publish_emergency_light(direction, remaining)
            time.sleep(1)
        # Al termine dell'emergency, torna a modalità standard
        with self.cycle_lock:
            self.active_mode = "standard"
            self.active_duration = self.standard_cycle
            self.active_direction = None
            self.pending_mode = None
            self.pending_duration = None
            self.pending_direction = None
            self.publish_standard_transition()

    def publish_red_light(self, direction, duration):
        msg = {
            "intersection": self.intersection_number,
            "e": {
                "n": "red_light",
                "u": "direction",
                "t": time.time(),
                "v": direction,
                "c": duration,
            }
        }
        self.client.myPublish(self.topic_status, msg)
        # Debug: print("Published:\n" + json.dumps(msg))

    def publish_green_light(self, direction, remaining):
        msg = {
            "intersection": self.intersection_number,
            "e": {
                "n": "green_light",
                "u": "direction",
                "t": time.time(),
                "v": direction,
                "c": remaining,
            }
        }
        self.client.myPublish(self.topic_status, msg)
        # Debug: print("Published green light message:\n" + json.dumps(msg))

    def publish_emergency_light(self, direction, remaining):
        """
        Pubblica il countdown del semaforo in emergenza.
        """
        msg = {
            "intersection": self.intersection_number,
            "e": {
                "n": "emergency_light",
                "u": "direction",
                "t": time.time(),
                "v": direction,
                "c": remaining,
                "i": self.intersection_number
            }
        }
        self.client.myPublish(self.topic_emergency, msg)

    def publish_standard_transition(self):
        """
        Publishes an MQTT message indicating the transition to standard mode.
        """
        msg = {
            "intersection": self.intersection_number,
            "e": {
                "n": "standard_transition",
                "t": time.time()
            }
        }
        self.client.myPublish(self.topic_trans, msg)
        print("Published standard transition message.")

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
    parent_dir2 = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    resource_catalog_path = os.path.join(parent_dir2, "SmartTrafficLight", "resource_catalog", "resource_catalog_info.json")
    led_info_path = os.path.join(script_dir, "LED_light2_info.json")

    info = json.load(open(led_info_path))

    led = LEDLights(info, resource_catalog_path)

    # Start background and foreground threads
    threading.Thread(name='background', target=led.background).start()
    threading.Thread(name='foreground', target=led.foreground).start()

    while True:
        time.sleep(0.5)