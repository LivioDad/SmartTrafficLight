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
        self.topic_red = led_info["servicesDetails"][0]["topic_red"]
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
        """
        Callback per i messaggi MQTT.
        Il nuovo comando viene memorizzato come pending e verrà applicato al termine del ciclo corrente.
        Se c'è già un comando emergency (attivo o pending), i comandi non-emergency vengono ignorati.
        """
        payload = json.loads(payload)
        # Imposta valori di default: se non viene specificato, il comando è "standard"
        new_mode = "standard"
        new_duration = self.standard_cycle
        new_direction = None

        if topic == self.topic_zone + f'/{self.intersection_number}':
            if payload["e"]["v"] == 'vulnerable_pedestrian':
                new_mode = "vulnerable"
                new_duration = self.vulnerable_cycle
            elif payload["e"]["v"] == 'pedestrian':
                new_mode = "pedestrian"
                new_duration = self.pedestrian_cycle

        elif topic == self.topic_emergency:
            if payload["zone"] == self.zone:
                new_mode = "emergency"
                new_duration = self.emergency_cycle
                new_direction = payload["direction"]
                print(f"Emergency announced in zone {payload['zone']} for direction {new_direction}")

        with self.cycle_lock:
            # Se c'è già un comando emergency (attivo o pendente) e il nuovo non lo è, ignoriamo l'update.
            if ((self.active_mode == "emergency") or (self.pending_mode == "emergency")) and (new_mode != "emergency"):
                print("Ignoring non-emergency command while emergency is active/pending.")
                return
            # Altrimenti, impostiamo il comando pendente.
            self.pending_mode = new_mode
            self.pending_duration = new_duration
            self.pending_direction = new_direction
        print("Pending command set:", self.pending_mode)

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
        time.sleep(duration)

        # Fase 2: NS rosso, WE verde
        self.NS_green.off()
        self.NS_red.on()
        self.WE_green.on()
        self.WE_red.off()
        self.publish_red_light("NS", duration)
        time.sleep(duration)

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

        time.sleep(duration)
        # Al termine dell'emergency, torna a modalità standard
        with self.cycle_lock:
            self.active_mode = "standard"
            self.active_duration = self.standard_cycle
            self.active_direction = None

    def publish_red_light(self, direction, duration):
        msg = {
            "intersection": self.intersection_number,
            "e": {
                "n": "red_light",
                "u": "direction",
                "t": time.time(),
                "v": direction,
                "c": duration
            }
        }
        self.client.myPublish(self.topic_red, msg)
        # Debug: print("Published:\n" + json.dumps(msg))

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
    led_info_path = os.path.join(script_dir, "LED_semaforo1_info.json")

    info = json.load(open(led_info_path))

    led = LEDLights(info, resource_catalog_path)

    # Start background and foreground threads
    threading.Thread(name='background', target=led.background).start()
    threading.Thread(name='foreground', target=led.foreground).start()

    while True:
        time.sleep(0.5)