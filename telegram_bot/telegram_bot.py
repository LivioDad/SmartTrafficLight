import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
import time
import json
import requests
import threading
import os
from urllib.parse import urlencode
from datetime import datetime
from dynamic_charts import generate_chart

def format_date(ts):
    try:
        return datetime.fromtimestamp(float(ts)).strftime("%d-%m-%Y %H:%M:%S")
    except:
        return str(ts)

def convert_to_iso_date(date_str):
    try:
        dt = datetime.strptime(date_str, "%d-%m-%Y")
        return dt.strftime("%Y-%m-%d")
    except:
        return date_str

class MyBot:
    def __init__(self, token, service_catalog_info_path, resource_info_path, police_password):
        self.tokenBot = token
        self.police_password = police_password

        with open(service_catalog_info_path) as f:
            catalog_info = json.load(f)
            self.catalog_url = f"http://{catalog_info['ip_address']}:{catalog_info['ip_port']}"

        with open(resource_info_path) as f:
            self.resource_info = json.load(f)

        self.db_connector_url = self.get_db_connector_url()
        self.authenticated_users = set()
        self.search_params = {}

        self.environment_zones = {
            "a": {
                "name": "Zone A",
                "api_url": "https://api.thingspeak.com/channels/2875299/feeds.json?api_key=BTP4K708D2767EMW&results=20",
                "chart_url_temp": "https://thingspeak.com/channels/2875299/charts/1?bgcolor=%23ffffff&dynamic=true&type=line",
                "chart_url_hum": "https://thingspeak.com/channels/2875299/charts/2?bgcolor=%23ffffff&dynamic=true&type=line"
            }
        }

        self.bot = telepot.Bot(self.tokenBot)
        MessageLoop(self.bot, {'chat': self.on_chat_message, 'callback_query': self.on_callback_query}).run_as_thread()

    def register_to_catalog(self):
        while True:
            try:
                self.resource_info['lastUpdate'] = time.time()
                requests.put(f"{self.catalog_url}/registerResource", json=self.resource_info)
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
            return None
        except:
            return None
        
    def send_main_menu(self, chat_ID):
        is_logged_in = chat_ID in self.authenticated_users
        login_note = "\n👤 Logged in as authorized agent" if is_logged_in else ""

        keyboard_buttons = [
            [InlineKeyboardButton(text="🌿 Environmental Data", callback_data="menu_environment")],
            [InlineKeyboardButton(text="🚗 Search by Plate (no auth)", callback_data="menu_plate")]
        ]

        # Add advanced search options if user is logged in
        if is_logged_in:
            keyboard_buttons.append([InlineKeyboardButton(text="🔍 Advanced Search", callback_data="menu_advanced")])

        keyboard_buttons.append([
            InlineKeyboardButton(
                text="🚪 Logout" if is_logged_in else "🔐 Login (for advanced search)",
                callback_data="menu_logout" if is_logged_in else "menu_login"
            )
        ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        self.bot.sendMessage(
            chat_ID,
            f"👋 Welcome to SmartTrafficLight Bot!{login_note}\n🚦 What would you like to do?",
            reply_markup=keyboard
        )

    def on_chat_message(self, msg):
        content_type, chat_type, chat_ID = telepot.glance(msg)
        message = msg['text'].strip()

        if message.lower() in ["/start", "/home"]:
            self.send_main_menu(chat_ID)
        elif message.lower() == "/environment":
            self.handle_environment_data(chat_ID)
        elif message.lower() == "/plate":
            self.search_params[chat_ID] = {"mode": "plate_only"}
            self.bot.sendMessage(chat_ID, "🚗 Enter your license plate:")
        elif message.lower() == "/violations":
            self.bot.sendMessage(chat_ID, "🔐 Please enter your authentication password:\n/auth <password>")
        elif message.lower().startswith("/auth"):
            self.authenticate_user(chat_ID, message)
        elif message.lower() == "/logout":
            self.logout_user(chat_ID)
        elif chat_ID in self.search_params:
            self.collect_search_params(chat_ID, message)
        else:
            self.send_main_menu(chat_ID)

    def on_callback_query(self, msg):
        query_ID, from_ID, query_data = telepot.glance(msg, flavor='callback_query')

        if query_data.startswith("menu_"):
            self.bot.answerCallbackQuery(query_ID)

            if query_data == "menu_environment":
                self.handle_environment_data(from_ID)

            elif query_data == "menu_plate":
                self.search_params[from_ID] = {"mode": "plate_only"}
                self.bot.sendMessage(from_ID, "🚗 Enter your license plate:")

            elif query_data == "menu_login":
                self.bot.sendMessage(from_ID, "🔐 Please enter your authentication password:\n/auth <password>")

            elif query_data == "menu_logout":
                self.logout_user(from_ID)

            elif query_data == "menu_advanced":
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔎 By Plate", callback_data="plate")],
                    [InlineKeyboardButton(text="🚦 By Semaphore ID", callback_data="semaphore")],
                    [InlineKeyboardButton(text="📅 By Date Range", callback_data="date_range")]
                ])
                self.bot.sendMessage(from_ID, "🔍 Choose advanced search criteria:", reply_markup=keyboard)
            return

        if query_data == "download_csv":
            self.bot.answerCallbackQuery(query_ID)

            results = getattr(self, "search_results", {}).get(from_ID)
            if not results:
                self.bot.sendMessage(from_ID, "⚠️ No results available for download.")
                return

            filename = f"violations_{from_ID}.csv"
            with open(filename, "w", encoding="utf-8") as f:
                f.write("Plate,Date,Station\n")
                for r in results:
                    date_str = format_date(r['date'])
                    f.write(f"{r['plate']},{date_str},{r['station']}\n")

            with open(filename, "rb") as f:
                self.bot.sendDocument(from_ID, f, caption="📎 Violations CSV exported")

            os.remove(filename)
            return

        # Set search mode based on user selection (plate/semaphore/date_range)
        self.search_params[from_ID] = {"mode": query_data}
        self.bot.answerCallbackQuery(query_ID, text=f"Search by {query_data.replace('_', ' ').title()} selected.")

        if query_data == "plate":
            self.bot.sendMessage(from_ID, "🚗 Enter license plate:")
        elif query_data == "semaphore":
            self.bot.sendMessage(from_ID, "🚦 Enter semaphore ID:")
        elif query_data == "date_range":
            self.bot.sendMessage(from_ID, "📅 Enter start date (DD-MM-YYYY):")

    def authenticate_user(self, chat_ID, message):
        parts = message.split()
        if len(parts) == 2 and parts[1] == self.police_password:
            self.authenticated_users.add(chat_ID)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔎 By Plate", callback_data="plate")],
                [InlineKeyboardButton(text="🚦 By Semaphore ID", callback_data="semaphore")],
                [InlineKeyboardButton(text="📅 By Date Range", callback_data="date_range")]
            ])
            self.bot.sendMessage(chat_ID, "✅ Authenticated! Choose your search criteria:", reply_markup=keyboard)
        else:
            self.bot.sendMessage(chat_ID, "❌ Incorrect password.")

    def logout_user(self, chat_ID):
        if chat_ID in self.authenticated_users:
            self.authenticated_users.remove(chat_ID)
            self.bot.sendMessage(chat_ID, "✅ You have been logged out.")
        else:
            self.bot.sendMessage(chat_ID, "⚠️ You are not logged in.")
        self.send_main_menu(chat_ID)

    def handle_environment_data(self, chat_ID):
        self.search_params[chat_ID] = {"mode": "environment"}
        self.bot.sendMessage(chat_ID, "🏞️ Enter the zone name (A,B,..):")

    def collect_search_params(self, chat_ID, message):
        if message.strip().lower() == "exit":
            self.search_params.pop(chat_ID, None)
            self.bot.sendMessage(chat_ID, "✅ Search session ended.")
            self.send_main_menu(chat_ID)
            return

        params = self.search_params[chat_ID]
        mode = params["mode"]

        # Simple helper to validate date format
        def validate_date_format(date_str):
            try:
                datetime.strptime(date_str, "%d-%m-%Y")
                return True
            except ValueError:
                return False

        if mode == "environment":
            zone_key = message.strip().lower()
            zone = self.environment_zones.get(zone_key)

            if not zone:
                self.bot.sendMessage(chat_ID, "❌ Zone not found. Try again or type 'exit' to cancel.")
                return

            try:
                response = requests.get(zone["api_url"])
                if response.status_code == 200:
                    data = response.json()
                    feeds = data.get("feeds", [])
                    temperature = humidity = None
                    for entry in reversed(feeds):
                        if temperature is None and entry.get("field1"):
                            temperature = entry["field1"]
                        if humidity is None and entry.get("field2"):
                            humidity = entry["field2"]
                        if temperature and humidity:
                            break
                    if temperature or humidity:
                        self.bot.sendMessage(chat_ID,
                            f"📍 *{zone['name']}*\n"
                            f"🌡️ Temperature: *{temperature or 'N/A'}°C*\n"
                            f"💧 Humidity: *{humidity or 'N/A'}%*",
                        parse_mode="Markdown")
                        temp_path = os.path.join(os.path.dirname(__file__),"charts", "temp_chart.png")
                        generate_chart(api_key="BTP4K708D2767EMW", field=1, ylabel="Temperature (°C)", filename=temp_path)
                        with open(temp_path, "rb") as temp_img:
                            self.bot.sendPhoto(chat_ID, temp_img, caption="📈 Temperature trend")
                        hum_path = os.path.join(os.path.dirname(__file__),"charts", "hum_chart.png")
                        generate_chart(api_key="BTP4K708D2767EMW", field=2, ylabel="Humidity (%)", filename=hum_path)
                        with open(hum_path, "rb") as hum_img:
                            self.bot.sendPhoto(chat_ID, hum_img, caption="📈 Humidity trend")
                    else:
                        self.bot.sendMessage(chat_ID, "No valid environmental data.")
                else:
                    self.bot.sendMessage(chat_ID, "❌ Failed to fetch data.")
            except Exception as e:
                self.bot.sendMessage(chat_ID, f"❌ Error: {e}")

            self.search_params.pop(chat_ID, None)
            self.send_main_menu(chat_ID)
            return

        if mode == "plate_only":
            self.execute_search(chat_ID, {"plate": message})
            return

        if mode == "plate" and "plate" not in params:
            params["plate"] = message
            self.execute_search(chat_ID, {"plate": message})

        elif mode == "semaphore" and "semaforo_id" not in params:
            params["semaforo_id"] = message
            self.execute_search(chat_ID, {"station": message})

        elif mode == "date_range":
            if message.strip().lower() == "edit start":
                params.pop("from_date", None)
                params.pop("to_date", None)
                self.bot.sendMessage(chat_ID, "✏️ Enter new start date (DD-MM-YYYY):")
                return

            if "from_date" not in params:
                if not validate_date_format(message):
                    self.bot.sendMessage(chat_ID, "⚠️ Invalid date format. Use DD-MM-YYYY.")
                    return
                params["from_date"] = message
                self.bot.sendMessage(chat_ID, "📅 Enter end date (DD-MM-YYYY):")

            elif "to_date" not in params:
                if not validate_date_format(message):
                    self.bot.sendMessage(chat_ID, "⚠️ Invalid date format. Use DD-MM-YYYY.")
                    return
                params["to_date"] = message
                self.execute_search(chat_ID, {
                    "from": params["from_date"] + "T00:00:00",
                    "to": params["to_date"] + "T23:59:59"
                }, repeat=True)

    def execute_search(self, chat_ID, filters, repeat=False):
        db_url = self.get_db_connector_url()
        if not db_url:
            self.bot.sendMessage(chat_ID, "Database Connector unavailable.")
            return

        if not repeat:
            self.search_params.pop(chat_ID, None)
        else:
            if "from" in filters and "to" in filters:
                self.search_params[chat_ID] = {
                    "mode": "date_range",
                    "from_date": filters["from"][:10]
                }
                self.bot.sendMessage(chat_ID, "📝 Enter new end date (DD-MM-YYYY), type 'edit start' to change start date, or 'exit' to stop:")

                db_url = self.get_db_connector_url()
                if not db_url:
                    self.bot.sendMessage(chat_ID, "Database Connector unavailable.")
                    return

        url = db_url.rstrip("/") + "/?" + urlencode(filters)

        try:
            response = requests.get(url)
            if response.status_code == 200:
                violations = response.json()
                if violations:
                    reply = "\n".join([
                        f"Plate: {x['plate']}, Date: {format_date(x['date'])}, Semaphore: {x['station']}"
                        for x in violations
                    ])
                    self.search_results = getattr(self, "search_results", {})
                    self.search_results[chat_ID] = violations  # 🔸 Save results for export
                else:
                    reply = "✅ No violations found."
                    self.search_results = getattr(self, "search_results", {})
                    self.search_results[chat_ID] = []
            else:
                reply = "❌ Error retrieving data."
        except Exception as e:
            reply = f"❌ Error: {e}"

        self.bot.sendMessage(chat_ID, reply)

        # Show export button if at least 2 results are found
        if self.search_results.get(chat_ID) and len(self.search_results[chat_ID]) >= 2:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬇️ Download CSV", callback_data="download_csv")]
            ])
            self.bot.sendMessage(chat_ID, "📄 Export options:", reply_markup=keyboard)

        if chat_ID in self.authenticated_users:
            if "plate" in filters:
                self.search_params[chat_ID] = {"mode": "plate"}
                self.bot.sendMessage(chat_ID, "🔁 Enter another license plate or type 'exit' to stop:")
            elif "station" in filters:
                self.search_params[chat_ID] = {"mode": "semaphore"}
                self.bot.sendMessage(chat_ID, "🔁 Enter another semaphore ID or type 'exit' to stop:")
            elif "from" in filters:
                self.search_params[chat_ID] = {"mode": "date_range", "from_date": filters["from"][:10]}
        else:
            self.search_params[chat_ID] = {"mode": "plate_only"}
            self.bot.sendMessage(chat_ID, "🔁 Enter another license plate or type 'exit' to stop:")

if __name__ == "__main__":
    base_path = os.path.dirname(os.path.abspath(__file__))
    info_path = os.path.join(base_path, "telegram_bot_info.json")
    resource_catalog_path = os.path.normpath(os.path.join(base_path, "..", "resource_catalog", "resource_catalog_info.json"))

    with open(info_path, "r") as f:
        info_data = json.load(f)

    config = info_data["config"][0]
    token = config['token']
    police_password = config['police_password']

    bot = MyBot(token, resource_catalog_path, info_path, police_password)
    threading.Thread(target=bot.register_to_catalog, daemon=True).start()

    while True:
        time.sleep(3)