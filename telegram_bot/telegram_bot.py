import telepot
from telepot.loop import MessageLoop
import time
import json
import requests
from urllib.parse import urlencode

class MyBot:

    def __init__(self, token, service_catalog_url, police_password):
        self.tokenBot = token
        self.service_catalog_url = service_catalog_url
        self.police_password = police_password

        self.db_connector_url = self.get_db_connector_url()

        self.authenticated_users = set()
        self.search_params = {}

        self.bot = telepot.Bot(self.tokenBot)
        MessageLoop(self.bot, {'chat': self.on_chat_message}).run_as_thread()

    def get_db_connector_url(self):
        """ Retrieve the Database Connector URL from the Service Catalog """
        try:
            response = requests.get(f"{self.service_catalog_url}/services")
            services = response.json()

            for service in services:
                if service['name'] == 'DatabaseConnector':
                    return service['url']

            print("DatabaseConnector not found in the catalog")
            return None
        except Exception as e:
            print(f"Error retrieving from the catalog: {e}")
            return None

    def on_chat_message(self, msg):
        """ Handle incoming Telegram messages """
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
        # ask the authenticated user the paramethers of the research
        elif chat_ID in self.authenticated_users:
            if chat_ID in self.search_params:
                self.collect_search_params(chat_ID, message)
            else:
                self.bot.sendMessage(chat_ID, "Unrecognized command. Use /help for available commands.")
        else:
            self.bot.sendMessage(chat_ID, "Unrecognized command or authentication required.")

    def authenticate_user(self, chat_ID, message):
        """ Authenticate the user using a password 
            The incoming message is composed by two parts: /auth password
        """
        parts = message.split()
        if len(parts) == 2 and parts[1] == self.police_password:
            self.authenticated_users.add(chat_ID)
            self.bot.sendMessage(chat_ID, "✅ Authentication successful! You can now use /search to query violations.")
        else:
            self.bot.sendMessage(chat_ID, "❌ Incorrect password.")

    def handle_environment_data(self, chat_ID):
        """ Retrieve environmental data from an API """
        try:
            response = requests.get("https://api.thingspeak.com/channels/YOUR_CHANNEL_ID/fields/1.json?api_key=YOUR_API_KEY")
            if response.status_code == 200:
                data = response.json()
                temperature = data.get('temperature', 'N/A')
                humidity = data.get('humidity', 'N/A')
                self.bot.sendMessage(chat_ID, f"Environmental Data:\n- Temperature: {temperature}°C\n- Humidity: {humidity}%")
            else:
                self.bot.sendMessage(chat_ID, "❌ Failed to retrieve environmental data.")
        except Exception as e:
            self.bot.sendMessage(chat_ID, f"❌ Error: {e}")

    def logout_user(self, chat_ID):
        """ Log out the user """
        if chat_ID in self.authenticated_users:
            self.authenticated_users.remove(chat_ID)
            self.bot.sendMessage(chat_ID, "✅ You have been logged out.")
        else:
            self.bot.sendMessage(chat_ID, "⚠️ You are not logged in.")

    # these methods are available only to authenticated users
    def start_search(self, chat_ID):
        """ Start the guided search process """
        self.search_params[chat_ID] = {}
        self.bot.sendMessage(chat_ID, "🔎 Do you want to search by license plate? (Type the plate number or leave empty for all)")

    def collect_search_params(self, chat_ID, message):
        """ Collect search parameters step by step 
            We store all the parameters inside a dictionary:
            query_params = {
                                "targa": "AB123CD",
                                "semaforo_id": "15",
                                "from": "2025-03-01T00:00:00",
                                "to": "2025-03-05T23:59:59"
                            }
        """
        params = self.search_params[chat_ID]

        if "targa" not in params:
            params["targa"] = message if message else None
            self.bot.sendMessage(chat_ID, "📍 Do you want to filter by semaphore? (Enter the ID or leave empty).")
        elif "semaforo_id" not in params:
            params["semaforo_id"] = message if message else None
            self.bot.sendMessage(chat_ID, "🗓️ Enter the start date (format: YYYY-MM-DD) or leave empty.")
        elif "from_date" not in params:
            params["from_date"] = message if message else None
            self.bot.sendMessage(chat_ID, "🗓️ Enter the end date (format: YYYY-MM-DD) or leave empty.")
        elif "to_date" not in params:
            params["to_date"] = message if message else None
            self.execute_search(chat_ID)

    def execute_search(self, chat_ID):
        """ Perform the actual query to the Database Connector """
        # params alone is a dictionary
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
        # e.g. http://db_connector/infrazioni?targa=AB123CD&semaforo_id=15&from=2025-03-01T00%3A00%3A00&to=2025-03-05T23%3A59%3A59

        url = f"{self.db_connector_url}/infrazioni?{query_string}"

        try:
            response = requests.get(url)
            if response.status_code == 200:
                violations = response.json()
                if violations:
                    reply = "\n".join([f"Plate: {x['targa']}, Date: {x['timestamp']}, Semaphore: {x['semaforo_id']}" for x in violations])
                else:
                    reply = "✅ No violations found."
            else:
                reply = "❌ Error retrieving data from the Database Connector."
        except Exception as e:
            reply = f"❌ Error: {e}"

        self.bot.sendMessage(chat_ID, reply)

if __name__ == "__main__":
    config = json.load(open('config.json'))
    service_catalog_url = config["catalogURL"]
    token = config['token']
    police_password = config['police_password']

    bot = MyBot(token, service_catalog_url, police_password)
    while True:
        time.sleep(3)
