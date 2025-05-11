import time
import json
import threading
import os
from LCD_config import LCD
from MyMQTT import MyMQTT
import requests
import os
import threading

""" Script per gestire un LCD destinato ad essere posizionato sul semaforo A1 in direzione NS """

class LCDSubscriber:
    def __init__(self, lcd_manager_info, resource_catalog_info):
        # Load the configuration
        self.resource_catalog_info_info = json.load(open(resource_catalog_info))
        led_info = json.load(open(lcd_manager_info))

        self.lcd_manager_info = lcd_manager_info
        # Request information from the resource catalog
        request_string = f'http://{self.resource_catalog_info_info["ip_address"]}:{self.resource_catalog_info_info["ip_port"]}/broker'
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["name"]
        self.port = rjson["port"]

        # Estrae i topic dalla configurazione
        for s in led_info["serviceDetails"]:
            if s["serviceType"] == 'MQTT':
                self.topicS = s["topic_subscribe"]
                self.topicE = s["topic_emergency"]
                self.topicStatus = s["topic_status"]
                self.topicTransition = s["topic_transition"]
                self.topicRoadIce = s["topic_roadice"]
        self.intersection_number = led_info["Name"].split('_')[2]
        
        self.clientID = led_info["Name"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, self)

        # Inizializza l'LCD
        self.lcd = LCD(2, 0x27, True)

        # Stato dell'LCD
        self.line1_text = ""  # Per warning o stato principale
        self.line2_text = ""  # Per il countdown

        # Inizializza controllo del countdown
        self.countdown_thread = None
        self.stop_countdown_flag = threading.Event()

        self.update_display("Waiting for", "sensor data...")

    def register(self):
        request_string = 'http://' + self.resource_catalog_info_info["ip_address"] + ':' + self.resource_catalog_info_info["ip_port"] + '/registerResource'
        data = json.load(open(self.lcd_manager_info))
        try:
            r = requests.put(request_string, json.dumps(data, indent=4))
            print(f'Response: {r.text}')
        except:
            print("An error occurred during registration")

    def centered_message(self, text, line):
        """ Centra il testo su una riga dell'LCD """
        lcd_width = 16
        text = text.center(lcd_width)
        self.lcd.message(text, line)

    def update_display(self, line1=None, line2=None):
        """ Aggiorna solo le righe modificate dell'LCD """
        if line1 is not None and line1 != self.line1_text:
            self.line1_text = line1
            self.centered_message(line1, 1)
        if line2 is not None and line2 != self.line2_text:
            self.line2_text = line2
            self.centered_message(line2, 2)
            
    def notify(self, topic, payload):
        """ Callback for incoming MQTT messages """
        try:
            message_received = json.loads(payload)

            # Handle ice risk messages first
            if topic == self.topicRoadIce:
                try:
                    for e in message_received["e"]:
                        if e["n"] == "ice_risk" and e["v"] > 0.5:
                            self.stop_countdown()
                            self.show_warning("ICE RISK!")
                            return
                except Exception as ex:
                    print(f"Error parsing ice_risk message: {ex}")
                return  # Exit after processing

            # Legacy pedestrian/emergency handlers
            if "e" in message_received and isinstance(message_received["e"], dict):
                event = message_received["e"].get("n")

                if event == "vul_button":
                    self.stop_countdown()
                    self.show_warning("VULNERABLE USER!")
                    return
                if event == "ped_sens":
                    self.stop_countdown()
                    self.show_warning("PEDESTRIAN CROSS!")
                    return
                if event == "standard_transition":
                    self.stop_countdown()
                    self.update_display(line1="", line2="")
                    return

                if event in ["green_light", "red_light"]:
                    if message_received["e"]["v"] == "NS":
                        duration = message_received["e"]["c"]
                        template = "Red in {}s" if event == "green_light" else "Green in {}s"
                        self.stop_countdown()
                        self.start_countdown(template, duration)
                    return

                if event == "emergency_light":
                    if message_received["e"]["i"] == self.intersection_number:
                        duration = message_received["e"]["c"]
                        self.stop_countdown()
                        self.update_display(line1="EMERG VEHICLE!")
                        self.start_countdown("Clear in {} sec", duration)
                    return

        except Exception as e:
            print(f"Error processing message: {e}")

    def show_warning(self, message):
        """ Visualizza un messaggio di warning sull'LCD """
        self.update_display(line1=message)

    def start_countdown(self, message_template, duration):
        """ Avvia un thread dedicato per aggiornare il countdown """
        self.stop_countdown_flag.clear()
        self.countdown_thread = threading.Thread(target=self._countdown, args=(message_template, duration))
        self.countdown_thread.start()

    def _countdown(self, message_template, duration):
        remaining = duration
        while remaining > 0 and not self.stop_countdown_flag.is_set():
            self.update_display(line2=message_template.format(remaining))
            time.sleep(0.85)
            remaining -= 1
        if not self.stop_countdown_flag.is_set():
            self.update_display(line2="")

    def stop_countdown(self):
        """ Ferma il countdown corrente, se attivo """
        if self.countdown_thread and self.countdown_thread.is_alive():
            self.stop_countdown_flag.set()
            self.countdown_thread.join()
        self.countdown_thread = None
        self.stop_countdown_flag.clear()

    def start(self):
        """ Avvia il client MQTT e sottoscrive ai topic """
        self.client.start()
        time.sleep(3)  # Tempo per la connessione
        self.client.mySubscribe(self.topicS)
        self.client.mySubscribe(self.topicE)
        self.client.mySubscribe(self.topicStatus)
        self.client.mySubscribe(self.topicTransition)
        self.client.mySubscribe(self.topicRoadIce)

    def stop(self):
        """ Ferma il client MQTT """
        self.client.unsubscribe()
        time.sleep(3)
        self.client.stop()

    def background(self):
        while True:
            self.register()
            time.sleep(10)

    def foreground(self):
        self.start()

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    parent_dir1 = os.path.dirname(parent_dir)
    lcd_manager_info_path = os.path.join(script_dir, 'LCD_info.json')
    resource_catalog_info_path = os.path.join(parent_dir1, 'resource_catalog', 'resource_catalog_info.json')

    lcd_subscriber = LCDSubscriber(lcd_manager_info_path, resource_catalog_info_path)

    b = threading.Thread(name='background', target=lcd_subscriber.background)
    f = threading.Thread(name='foreground', target=lcd_subscriber.foreground)

    b.start() #activate the backgorund periodically register
    f.start() #activate the subscirpiton to MQTT topics

    try:
        while True:
            time.sleep(1)  # Mantiene il programma in esecuzione
    except KeyboardInterrupt:
        print("\nStopping LCD MQTT Subscriber...")
        lcd_subscriber.stop()
        print("Stopped.")
