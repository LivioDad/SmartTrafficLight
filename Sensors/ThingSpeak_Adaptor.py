import requests
import json
from MyMQTT import *
import time
import uuid
import os
from dotenv import load_dotenv
load_dotenv('/app/.env')

# This script recieves data from the DHT22 sensor via MQTT and sends it to Thingspeak.
# Due to Thingspeak limitations on a free plan, it sends the temperature and humidity values alternately every 15 seconds.

class Thingspeak_Adaptor:
    def __init__(self,settings):
        self.settings = settings
        self.catalogURL=settings['catalogURL']
        self.serviceInfo=settings['serviceInfo']
        self.baseURL=self.settings["ThingspeakURL"]
        self.channelWriteAPIkey = os.getenv("THINGSPEAK_WRITE_KEY")
        self.channelReadAPIkey = os.getenv("THINGSPEAK_READ_KEY")
        self.broker=self.settings["brokerIP"]
        self.port=self.settings["brokerPort"]
        self.topic=self.settings["mqttTopic"]+"/#"
        self.mqttClient = MyMQTT(clientID=str(uuid.uuid1()), broker=self.broker, port=self.port, notifier=self) #uuid is to generate a random string for the client id
        self.mqttClient.start()
        self.mqttClient.mySubscribe(self.topic)
        self.actualTime = time.time()
        self.valuetotransmit = "temp"
    
    def registerService(self):
        self.serviceInfo['last_update']=self.actualTime
        requests.post(f'{self.catalogURL}/services',data=json.dumps(self.serviceInfo))
    
    def updateService(self):
        self.serviceInfo['last_update']=self.actualTime
        requests.put(f'{self.catalogURL}/services',data=json.dumps(self.serviceInfo))

    def stop(self):
        self.mqttClient.stop()
    
    def notify(self,topic,payload):
        #{'bn':f'SensorREST_MQTT_{self.deviceID}','e':[{'n':'humidity','v':'', 't':'','u':'%'}]}
        message_decoded=json.loads(payload)
        decide_measurement=message_decoded["e"][0]["n"]
        error = False
        if decide_measurement=="temperature" and self.valuetotransmit == "temp":
            #print("\n \n Temperature Message sent:")
            message_value=message_decoded["e"][0]['v']
            #print(message_decoded)
            r = self.uploadThingspeak(field_number=1,field_value=message_value)
            if r != "0":
                print(f"Temperature ({message_value} C) successfully delivered to TS at time: {time.strftime('%H:%M:%S', time.localtime(time.time()))}")
                self.valuetotransmit = "hum"

        if decide_measurement=="humidity" and self.valuetotransmit == "hum":
            #print("\n \n Humidity Message sent:")
            message_value=message_decoded["e"][0]['v']
            #print(message_decoded)
            r = self.uploadThingspeak(field_number=2,field_value=message_value)
            if r != "0":
                print(f"Humidity ({message_value} %) succesfully delivered to TS at time: {time.strftime('%H:%M:%S', time.localtime(time.time()))}")
                self.valuetotransmit = "temp"
            
    def uploadThingspeak(self,field_number,field_value):
        #GET https://api.thingspeak.com/update?api_key=N7GEPLVRH3PP72BP&field1=0
        #baseURL -> https://api.thingspeak.com/update?api_key=
        #Channel API KEY -> N7GEPLVRH3PP72BP Particular value for each Thingspeak channel
        #fieldnumber -> depends on the field (type of measurement) we want to upload the information to
        urlToSend=f'{self.baseURL}{self.channelWriteAPIkey}&field{field_number}={field_value}'
        r=requests.get(urlToSend)
        return r.text
    
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))  # Find the directory of the script
    settings_path = os.path.join(script_dir, "ThingSpeak_Adaptor_info.json")  # Build path to JSON file
    settings = json.load(open(settings_path))  # Load JSON file
    ts_adaptor=Thingspeak_Adaptor(settings)
    # ts_adaptor.registerService()
    try:
        counter=0
        while True:
            time.sleep(2)
            counter+=1
            if counter==20:
                # ts_adaptor.updateService()
                counter=0
    except KeyboardInterrupt:
        ts_adaptor.stop()
        print("Thingspeak Adaptor Stopped")