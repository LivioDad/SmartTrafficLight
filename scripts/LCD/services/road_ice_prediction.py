import paho.mqtt.client as mqtt
import requests
import joblib
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
import os

# Configuration
THINGSPEAK_URL = "https://api.thingspeak.com/update"
MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_TOPIC_SUBSCRIBE = "sensors/weather"
MQTT_TOPIC_PUBLISH = "alerts/ice_warning"
LCD_DISPLAY_TOPIC = "display/lcd"
MODEL_FILE = "data/linear_model.pkl"
DATASET_FILE = "data/ice_risk_dataset.json"

# Load dataset and train model if not exists
def train_model():
    df = pd.read_json(DATASET_FILE)
    X_train = df[["temperature", "humidity"]].values
    y_train = df["ice_risk"].values
    
    model = LinearRegression()
    model.fit(X_train, y_train)
    joblib.dump(model, MODEL_FILE)
    print("Model trained and saved.")
    return model

# Load or train model
if os.path.exists(MODEL_FILE):
    model = joblib.load(MODEL_FILE)
    print("Model loaded successfully.")
else:
    print("No model found, starting training.")
    model = train_model()

# Handle incoming MQTT messages
def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    temperature = payload.get("temperature")
    humidity = payload.get("humidity")
    
    if temperature is not None and humidity is not None:
        ice_risk = model.predict(np.array([[temperature, humidity]]))[0]
        print(f"Temp: {temperature}°C, Humidity: {humidity}% -> Ice Risk: {ice_risk:.2f}")
        
        if ice_risk > 0.5:
            alert_message = "Warning: Possible ice on the road!"
            client.publish(MQTT_TOPIC_PUBLISH, json.dumps({"alert": alert_message}))
            client.publish(LCD_DISPLAY_TOPIC, json.dumps({"message": alert_message}))
            print("Alert sent!")

# MQTT Configuration
client = mqtt.Client()
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.subscribe(MQTT_TOPIC_SUBSCRIBE)

print("Service started. Waiting for data...")
client.loop_forever()
