import telepot
from telepot.loop import MessageLoop
import time
import json
import requests
import threading
import os
from urllib.parse import urlencode

class MyBot:
    def __init__(self, token, service_catalog_info_path, resource_info_path, police_password):
        self.tokenBot = token
        self.police_password = police_password

        # Load catalog info
        with open(service_catalog_info_path) as f:
            catalog_info = json.load(f)
            self.catalog_url = f"http://{catalog_info['ip_address']}:{catalog_info['ip_port']}"

        # Load bot resource info
        with open(resource_info_path) as f:
            self.resource_info = json.load(f)

        # Discover DB Connector URL
        self.db_connector_url = self.get_db_connector_url()

        # Authenticated users and search params
        self.authenticated_users = set()
        self.search_params = {}

        # Telegram bot setup
        self.bot = telepot.Bot(self.tokenBot)
        MessageLoop(self.bot, {'chat': self.on_chat_message}).run_as_thread()

    def register_to_catalog(self):
        while True:
            try:
                self.resource_info['lastUpdate'] = time.time()
                response = requests.put(f"{self.catalog_url}/registerResource", json=self.resource_info)
                print(f"Catalog registration: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"Catalog registration error: {e}")
            time.sleep(10)

    def get_db_connector_url(self):
        try:
            response = requests.get(f"{self.catalog_url}/resourceID?ID=db_connector_1")
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

        # depending on whether the user is autenticated, show different options
        if message.lower() in ["/start", "/home"]:
            if chat_ID in self.authenticated_users:
                self.bot.sendMessage(chat_ID, 
                    "Welcome! Available commands:\n"
                    "/environment - Retrieve environmental data\n"
                    "/violations - Access traffic violations\n"
                    "/logout - Log out\n"
                    "/search - Start an advanced traffic violation search")
            else:
                self.bot.sendMessage(chat_ID, 
                    "Welcome! Available commands:\n"
                    "/environment - Retrieve environmental data\n"
                    "/violations - Access traffic violations (authentication required)\n"
                    "/logout - Log out")
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
            self.bot.sendMessage(chat_ID, "✅ Authentication successful! You can now use /search to query violations.")
        else:
            self.bot.sendMessage(chat_ID, "❌ Incorrect password.")

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
                    self.bot.sendMessage(chat_ID, f"Environmental Data:\n- Temperature: {temperature}°C\n- Humidity: {humidity}%")
                else:
                    self.bot.sendMessage(chat_ID, "No data available from the sensor.")
            else:
                self.bot.sendMessage(chat_ID, "❌ Failed to retrieve environmental data.")
        except Exception as e:
            self.bot.sendMessage(chat_ID, f"❌ Error: {e}")

    def logout_user(self, chat_ID):
        if chat_ID in self.authenticated_users:
            self.authenticated_users.remove(chat_ID)
            self.bot.sendMessage(chat_ID, "✅ You have been logged out.")
        else:
            self.bot.sendMessage(chat_ID, "⚠️ You are not logged in.")

    def start_search(self, chat_ID):
        self.search_params[chat_ID] = {}
        self.bot.sendMessage(chat_ID, "🔎 Do you want to search by license plate? (Type the plate number or leave empty for all)")

    def collect_search_params(self, chat_ID, message):
        params = self.search_params[chat_ID]

        cleaned = message.strip()
        user_input = None if cleaned == "-" else cleaned

        if "targa" not in params:
            params["targa"] = user_input
            self.bot.sendMessage(chat_ID, "📍 Enter semaphore ID (or type '-' to skip):")
        elif "semaforo_id" not in params:
            params["semaforo_id"] = user_input
            self.bot.sendMessage(chat_ID, "🗓️ Enter start date (YYYY-MM-DD) or type '-' to skip:")
        elif "from_date" not in params:
            params["from_date"] = user_input
            self.bot.sendMessage(chat_ID, "🗓️ Enter end date (YYYY-MM-DD) or type '-' to skip:")
        elif "to_date" not in params:
            params["to_date"] = user_input
            self.execute_search(chat_ID)


    def execute_search(self, chat_ID):
        # extract paramethers specified by user
        params = self.search_params.pop(chat_ID)

        query_params = {}
        if params['targa']:
            query_params['targa'] = params['targa']
        if params['semaforo_id']:
            query_params['semaforo_id'] = params['semaforo_id']
        if params['from_date'] and params['to_date']:
            query_params['from'] = params['from_date'] + "T00:00:00"
            query_params['to'] = params['to_date'] + "T23:59:59"

        # dinamically discover the db adaptor url, if the telegram bot was started before adaptor
        # then the url will be None
        db_url = self.get_db_connector_url()
        if not db_url:
            self.bot.sendMessage(chat_ID, "❌ Database Connector not available.")
            return

        # build the url avoiding double slash
        #url = db_url.rstrip("/") + "/infrazioni?" + urlencode(query_params)
        url = db_url.rstrip("/") + "/?" + urlencode(query_params)


        try:
            response = requests.get(url)
            if response.status_code == 200:
                violations = response.json()
                if violations:
                    reply = "\n".join([
                        f"Plate: {x['plate']}, Date: {x['date']}, Semaphore: {x['station']}"
                        for x in violations
                    ])
                else:
                    reply = "✅ No violations found."
            else:
                reply = "❌ Error retrieving data from the Database Connector."
        except Exception as e:
            reply = f"❌ Error: {e}"

        self.bot.sendMessage(chat_ID, reply)

if __name__ == "__main__":
    import os

    base_path = os.path.dirname(os.path.abspath(__file__))
    info_path = os.path.join(base_path, "telegram_bot_info.json")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    resource_catalog_path = os.path.join(script_dir, "..", "resource_catalog", "resource_catalog_info.json")
    resource_catalog_path = os.path.normpath(resource_catalog_path)

    # Load config list from JSON
    with open(info_path, "r") as f:
        info_data = json.load(f)

    config = info_data["config"][0]

    token = config['token']
    police_password = config['police_password']

    bot = MyBot(token, resource_catalog_path, info_path, police_password)
    threading.Thread(target=bot.register_to_catalog, daemon=True).start()

    while True:
        time.sleep(3)
