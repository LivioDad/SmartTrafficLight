from MyMQTT import *
import requests
import joblib
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
import os
import threading
import requests
import time


class Predictor:
    def __init__(self, predictor_info, resource_catalog_file , dataset_file):
        # Retrieve broker info from service catalog
        self.resource_catalog = json.load(open(resource_catalog_file))
        request_string = 'http://' + self.resource_catalog["ip_address"] + ':' \
                        + self.resource_catalog["ip_port"] + '/broker'
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["name"]
        self.port = rjson["port"]

        # Details about sensor
        self.predictor_info = predictor_info
        info = json.load(open(self.predictor_info))
        self.topicS = info["servicesDetails"][0]["topicS"]
        self.topicP = info["servicesDetails"][0]["topicP"]
        self.clientID = info["ID"]
        self.client = MyMQTT(self.clientID, self.broker, self.port, self)

        self.dataset_file = dataset_file
        self.dataset = json.load(open(self.dataset_file))
        self.model = None
        self.model_file = "linear_model.pkl"
        # MODEL_FILE = "data/linear_model.pkl"
        self.take_model()


    def register(self):
        request_string = 'http://' + self.resource_catalog["ip_address"] + ':' + self.resource_catalog["ip_port"] + '/registerResource'
        data = json.load(open(self.predictor_info))
        try:
            r = requests.put(request_string, json.dumps(data, indent=4))
            print(f'Response: {r.text}')
        except:
            print("An error occurred during registration")
    
    def start(self):
        self.client.start()
        self.client.mySubscribe(self.topicS)

    def stop(self):
        self.client.unsubscribe()
        time.sleep(3)
        self.client.stop()

    def background(self):
        while True:
            self.register()
            time.sleep(10)

    def foreground(self):
        self.start()

    # Load dataset and train model if not exists
    def train_model(self):
        df = pd.DataFrame(self.dataset)
        X_train = df[["temperature", "humidity"]].values
        y_train = df["ice_risk"].values
        
        model = LinearRegression()
        model.fit(X_train, y_train)
        joblib.dump(model, self.model_file)
        print("Model trained and saved.")
        return model
    
    def take_model(self):
        # Load or train model
        if os.path.exists(self.model_file):
            self.model = joblib.load(self.model_file)
            print("Model loaded successfully.")
        else:
            print("No model found, starting training.")
            self.model = self.train_model()

    # Handle incoming MQTT messages
    def notify(self , payload):
        temperature = None
        humidity = None
        payload = json.loads(payload)
        timestamp = payload["bt"]
        for elm in payload["e"]:
            if elm["n"] == "temperature":
                temperature = elm["v"]
            elif elm["n"] == "humidity":
                humidity = elm["v"]
        
        if temperature is not None and humidity is not None:
            ice_risk = self.model.predict(np.array([[temperature, humidity]]))[0]
            print(f"Temp: {temperature}°C, Humidity: {humidity}% -> Ice Risk: {ice_risk:.2f}")
            
            if ice_risk > 0.5:
                message = {
                    "bn": self.clientID,
                    "bt": timestamp,
                    "e": [{
                        "n": "ice_risk",
                        "u": "%",
                        "v": ice_risk
                    }]
                }
                self.client.myPublish(self.topicP, message)
                print("Alert sent!")

# # MQTT Configuration
# client = mqtt.Client()
# client.on_message = on_message
# client.connect(MQTT_BROKER, MQTT_PORT, 60)
# client.subscribe(MQTT_TOPIC_SUBSCRIBE)

# print("Service started. Waiting for data...")
# client.loop_forever()


if __name__ == '__main__':
    # Lines to make automatically retrieve the path of resource_catalog_info.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    resource_catalog_path = os.path.join(script_dir, "..", "..", "..", "resource_catalog", "resource_catalog_info.json")
    resource_catalog_path = os.path.normpath(resource_catalog_path)
    road_ice_info_path = os.path.join(script_dir, "road_ice_info.json")
    road_ice_info_path = os.path.normpath(road_ice_info_path)
    train_dataset_path = os.path.join(script_dir, "road_ice_prediction.json")
    train_dataset_path = os.path.normpath(train_dataset_path)
    pred = Predictor(road_ice_info_path, resource_catalog_path , train_dataset_path)

    b = threading.Thread(name='background', target=pred.background)
    f = threading.Thread(name='foreground', target=pred.foreground)

    b.start()
    f.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Interrupted by user. Stopping services...")
        pred.stop()

    # try:
    #     while True:
    #         sens.read_dht11_data() # Read data from the DHT11 sensor
    #         time.sleep(5)  # Wait for 5 seconds before the next reading
    # except KeyboardInterrupt:
    #     print("Program interrupted.")
    # finally:
    #     sens.stop()