import time
import json
from MyMQTT import MyMQTT

# Configurazione broker MQTT
BROKER_ADDRESS = "test.mosquitto.org"
PORT = 1883
TOPIC = "SmartTrafficLight/Led/A"

class TrafficLightPublisher:
    def __init__(self, clientID, broker, port):
        self.clientID = clientID
        self.broker = broker
        self.port = port
        self.client = MyMQTT(clientID, broker, port, self)

    def start(self):
        self.client.start()

    def stop(self):
        self.client.stop()

    def notify(self, topic, payload):
        """Funzione necessaria per MyMQTT, ma non usata nel publisher."""
        pass

    def publish(self, state):
        """Invia un messaggio MQTT con lo stato del semaforo."""
        payload = json.dumps({"e": {"v": state}})
        self.client.myPublish(TOPIC, payload)
        print(f"Sent: {state}")

# Creazione del publisher
publisher = TrafficLightPublisher("TrafficLightController", BROKER_ADDRESS, PORT)
publisher.start()

# Definizione del ciclo semaforico
cycle_time = 2  # Durata in secondi per ogni stato

try:
    for _ in range(3):
        publisher.publish("red_WE")
        time.sleep(cycle_time)

        publisher.publish("green_WE")
        time.sleep(cycle_time)

        publisher.publish("red_NS")
        time.sleep(cycle_time)

        publisher.publish("green_NS")
        time.sleep(cycle_time)

    print("Traffic light simulation completed!")

finally:
    publisher.stop()
