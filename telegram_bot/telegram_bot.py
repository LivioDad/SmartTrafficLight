import telepot
from telepot.loop import MessageLoop
import time
import json
import requests
import threading
from urllib.parse import urlencode

class MyBot:
    def __init__(self, token, resource_catalog_file, telegram_info_path, police_password):

        # Retrieve broker info from service catalog
        self.resource_catalog = json.load(open(resource_catalog_file))
        request_string = 'http://' + self.resource_catalog["ip_address"] + ':' \
                         + self.resource_catalog["ip_port"] + '/broker'
        r = requests.get(request_string)
        rjson = json.loads(r.text)
        self.broker = rjson["name"]
        self.port = rjson["port"]
        self.tokenBot = token
        self.police_password = police_password
        self.telegram_info_path = telegram_info_path

        # Load bot resource info
        with open(telegram_info_path) as f:
            self.resource_info = json.load(f)

        # Discover DB Connector URL
        #self.db_connector_url = self.get_db_connector_url()
        self.db_connector_url = "http://127.0.0.1:8080"

        # Authenticated users and search params
        self.authenticated_users = set()
        self.search_params = {}

        # Telegram bot setup
        self.bot = telepot.Bot(self.tokenBot)
        MessageLoop(self.bot, {'chat': self.on_chat_message}).run_as_thread()

    def register(self):
        """Periodically register the sensor in the resource catalog."""
        request_string = f'http://{self.resource_catalog["ip_address"]}:{self.resource_catalog["ip_port"]}/registerResource'
        data = json.load(open(self.telegram_info_path))
        try:
            r = requests.put(request_string, json.dumps(data, indent=4))
            print(f'Response: {r.text}')
        except Exception as e:
            print(f'Error during registration: {e}')

    def get_db_connector_url(self):
        try:
            response = requests.get(f"{self.resource_catalog}/resourceID?ID=db_connector_1")
            if response.status_code == 200:
                service = response.json()
                for s in service.get("servicesDetails", []):
                    if s["serviceType"] == "REST":
                        return s["endpoint"]
            print("DatabaseConnector not found in catalog")
            return None
        except Exception as e:
            print(f"Error retrieving DB connector: {e}")
            return None

    def on_chat_message(self, msg):
        content_type, chat_type, chat_ID = telepot.glance(msg)
        message = msg['text'].strip()

        if message.lower() in ["/start", "/home"]:
            self.bot.sendMessage(chat_ID, 
                "Welcome! Available commands:\n"
                "/environment - Retrieve environmental data\n"
                "/violations - Access traffic violations (authentication required)\n"
                "/logout - Log out\n"
                "/search - Start an advanced traffic violation search")
        elif message.lower() == "/environment":
            self.handle_environment_data(chat_ID)
        elif message.lower() == "/violations":
            self.bot.sendMessage(chat_ID, "Please enter the authentication password:")
        elif message.lower() == "/logout":
            self.logout_user(chat_ID)
        elif message.startswith("/auth"):
            self.authenticate_user(chat_ID, message)
        elif message == "/search":
            self.start_search(chat_ID)
        elif chat_ID in self.authenticated_users:
            if chat_ID in self.search_params:
                self.collect_search_params(chat_ID, message)
            else:
                self.bot.sendMessage(chat_ID, "Unrecognized command. Use /help for available commands.")
        else:
            self.bot.sendMessage(chat_ID, "Unrecognized command or authentication required.")

    def authenticate_user(self, chat_ID, message):
        parts = message.split()
        if len(parts) == 2 and parts[1] == self.police_password:
            self.authenticated_users.add(chat_ID)
            self.bot.sendMessage(chat_ID, "\u2705 Authentication successful! You can now use /search to query violations.")
        else:
            self.bot.sendMessage(chat_ID, "\u274C Incorrect password.")

    def handle_environment_data(self, chat_ID):
        try:
            response = requests.get("https://api.thingspeak.com/channels/2875299/fields/1.json?api_key=BTP4K708D2767EMW")
            if response.status_code == 200:
                data = response.json()
                feeds = data.get("feeds", [])
                if feeds:
                    latest = feeds[-1]
                    temperature = latest.get("field1", "N/A")
                    humidity = latest.get("field2", "N/A")
                    self.bot.sendMessage(chat_ID, f"Environmental Data:\n- Temperature: {temperature}\u00b0C\n- Humidity: {humidity}%")
                else:
                    self.bot.sendMessage(chat_ID, "No data available from the sensor.")
            else:
                self.bot.sendMessage(chat_ID, "\u274C Failed to retrieve environmental data.")
        except Exception as e:
            self.bot.sendMessage(chat_ID, f"\u274C Error: {e}")

    def logout_user(self, chat_ID):
        if chat_ID in self.authenticated_users:
            self.authenticated_users.remove(chat_ID)
            self.bot.sendMessage(chat_ID, "\u2705 You have been logged out.")
        else:
            self.bot.sendMessage(chat_ID, "\u26a0\ufe0f You are not logged in.")

    def start_search(self, chat_ID):
        self.search_params[chat_ID] = {}
        self.bot.sendMessage(chat_ID, "\U0001F50E Do you want to search by license plate? (Type the plate number or leave empty for all)")

    def collect_search_params(self, chat_ID, message):
        params = self.search_params[chat_ID]

        if "targa" not in params:
            params["targa"] = message if message else None
            self.bot.sendMessage(chat_ID, "\ud83d\udccd Do you want to filter by semaphore? (Enter the ID or leave empty).")
        elif "semaforo_id" not in params:
            params["semaforo_id"] = message if message else None
            self.bot.sendMessage(chat_ID, "\ud83d\uddd3\ufe0f Enter the start date (format: YYYY-MM-DD) or leave empty.")
        elif "from_date" not in params:
            params["from_date"] = message if message else None
            self.bot.sendMessage(chat_ID, "\ud83d\uddd3\ufe0f Enter the end date (format: YYYY-MM-DD) or leave empty.")
        elif "to_date" not in params:
            params["to_date"] = message if message else None
            self.execute_search(chat_ID)

    def execute_search(self, chat_ID):
        params = self.search_params.pop(chat_ID)

        query_params = {}
        if params['targa']:
            query_params['targa'] = params['targa']
        if params['semaforo_id']:
            query_params['semaforo_id'] = params['semaforo_id']
        if params['from_date'] and params['to_date']:
            query_params['from'] = params['from_date'] + "T00:00:00"
            query_params['to'] = params['to_date'] + "T23:59:59"

        query_string = urlencode(query_params)
        url = f"{self.db_connector_url}/infrazioni?{query_string}"

        try:
            response = requests.get(url)
            if response.status_code == 200:
                violations = response.json()
                if violations:
                    reply = "\n".join([
                        f"Plate: {x['targa']}, Date: {x['timestamp']}, Semaphore: {x['semaforo_id']}"
                        for x in violations
                    ])
                else:
                    reply = "\u2705 No violations found."
            else:
                reply = "\u274C Error retrieving data from the Database Connector."
        except Exception as e:
            reply = f"\u274C Error: {e}"

        self.bot.sendMessage(chat_ID, reply)

if __name__ == "__main__":
    import os
    # Automatically retrieve the path of JSON config files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(script_dir,"config.json")
    parent_dir = os.path.dirname(script_dir)
    resource_catalog_path = os.path.join(parent_dir, "resource_catalog", "resource_catalog_info.json")
    telegram_info_path = os.path.join(script_dir, "telegram_bot_info.json")

    config = json.load(open(config_dir))
    token = config['token']
    police_password = config['police_password']

    bot = MyBot(token, resource_catalog_path, telegram_info_path, police_password)
    threading.Thread(target=bot.register).start()

    while True:
        time.sleep(3)
