import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
import time
import json
import requests
import threading
import os
import pytz
from urllib.parse import urlencode
from datetime import datetime
from dynamic_charts import generate_chart
from dotenv import load_dotenv
load_dotenv('/app/.env')

def format_date(ts):
    try:
        utc_dt = datetime.fromtimestamp(float(ts), tz=pytz.utc)
        local_dt = utc_dt.astimezone(pytz.timezone("Europe/Rome"))
        return local_dt.strftime("%d-%m-%Y %H:%M:%S")
    except:
        return str(ts)

def convert_to_iso_date(date_str):
    try:
        dt = datetime.strptime(date_str, "%d-%m-%Y")
        return dt.strftime("%Y-%m-%d")
    except:
        return date_str

class MyBot:
    def __init__(self, token, service_catalog_info_path, resource_info_path):
        self.tokenBot = os.getenv("TELEGRAM_BOT_TOKEN")
        self.police_password = os.getenv("POLICE_PASSWORD")
        self.thingspeak_api_key = os.getenv("THINGSPEAK_READ_KEY")

        with open(service_catalog_info_path) as f:
            catalog_info = json.load(f)
            self.catalog_url = f"http://{catalog_info['ip_address']}:{catalog_info['ip_port']}"

        with open(resource_info_path) as f:
            self.resource_info = json.load(f)

        self.db_connector_url = self.get_db_connector_url()
        self.authenticated_users = set()
        self.search_params = {}
        self.search_results = {}

        # Retrieve data from telegram_bot_info.json
        self.config_data = self.resource_info.get("config", [{}])[0]
        raw_zones = self.resource_info.get("environment_zones", {})
        self.environment_zones = {}

        channel_id = os.getenv("THINGSPEAK_CHANNEL_ID")
        for key, zone in raw_zones.items():
            self.environment_zones[key.lower()] = {
                "name": zone["name"],
                "api_url": f"https://api.thingspeak.com/channels/{channel_id}/feeds.json?api_key={self.thingspeak_api_key}&results=20",
                "chart_url_temp": f"https://thingspeak.com/channels/{channel_id}/charts/1?bgcolor=%23ffffff&dynamic=true&type=line",
                "chart_url_hum": f"https://thingspeak.com/channels/{channel_id}/charts/2?bgcolor=%23ffffff&dynamic=true&type=line"
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

        # Check authorization for restricted queries
        if query_data in ["semaphore", "date_range"] and from_ID not in self.authenticated_users:
            self.bot.sendMessage(from_ID, "❌ This function requires authentication.\n🔐 Please login with /auth <password>")
            return

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

            # Salva la zona scelta e chiedi quanti punti mostrare
            self.search_params[chat_ID] = {
                "mode": "environment_points",
                "zone_key": zone_key
            }
            self.bot.sendMessage(chat_ID, "📊 How many recent points do you want to display in the chart? (max 500)")
            return

        elif mode == "environment_points":
            if not message.isdigit():
                self.bot.sendMessage(chat_ID, "⚠️ Please enter a valid number.")
                return

            num_points = int(message)
            MAX_POINTS = 500

            if num_points < 1 or num_points > MAX_POINTS:
                self.bot.sendMessage(chat_ID, f"⚠️ Please enter a number between 1 and {MAX_POINTS}.")
                return

            zone_key = params["zone_key"]
            zone = self.environment_zones.get(zone_key)

            if not zone:
                self.bot.sendMessage(chat_ID, "❌ Zone not found. Try again or type 'exit'.")
                return

            try:
                chart_api_key = self.thingspeak_api_key

                temp_path = os.path.join(os.path.dirname(__file__), "charts", "temp_chart.png")
                generate_chart(field=1, ylabel="Temperature (°C)", filename=temp_path, results=num_points)
                with open(temp_path, "rb") as temp_img:
                    self.bot.sendPhoto(chat_ID, temp_img, caption=f"📈 Temperature trend (last {num_points} points)")

                hum_path = os.path.join(os.path.dirname(__file__), "charts", "hum_chart.png")
                generate_chart(field=2, ylabel="Humidity (%)", filename=hum_path, results=num_points)
                with open(hum_path, "rb") as hum_img:
                    self.bot.sendPhoto(chat_ID, hum_img, caption=f"📈 Humidity trend (last {num_points} points)")

            except Exception as e:
                self.bot.sendMessage(chat_ID, f"❌ Error generating charts: {e}")

            self.search_params.pop(chat_ID, None)
            self.send_main_menu(chat_ID)
            return

        if mode == "plate_only":
            plate = message.strip().upper() # Accept plate also if the user types it in lowercase
            self.execute_search(chat_ID, {"plate": plate})
            return

        if mode == "plate" and "plate" not in params:
            plate = message.strip().upper()
            params["plate"] = plate
            self.execute_search(chat_ID, {"plate": plate})

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
                ts = time.mktime(datetime.strptime(message, "%d-%m-%Y").replace(hour=0, minute=0, second=0).timetuple())
                params["from_date"] = str(int(ts))
                self.bot.sendMessage(chat_ID, "📅 Enter end date (DD-MM-YYYY):")
                return

            if "to_date" not in params:
                if not validate_date_format(message):
                    self.bot.sendMessage(chat_ID, "⚠️ Invalid date format. Use DD-MM-YYYY.")
                    return
                ts = time.mktime(datetime.strptime(message, "%d-%m-%Y").replace(hour=23, minute=59, second=59).timetuple())
                params["to_date"] = str(int(ts))

            if "from_date" in params and "to_date" in params:
                try:
                    self.execute_search(chat_ID, {
                        "from": params["from_date"],
                        "to": params["to_date"]
                    }, repeat=True)
                except Exception as e:
                    self.bot.sendMessage(chat_ID, f"❌ Error: {e}")
                return

    def execute_search(self, chat_ID, filters, repeat=False):
        db_url = self.get_db_connector_url()
        if not db_url:
            self.bot.sendMessage(chat_ID, "Database Connector unavailable.")
            return

        if not repeat:
            self.search_params.pop(chat_ID, None)

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
                    self.search_results[chat_ID] = violations  # Save results for export
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

        # Re-prompt after results if date_range mode
        if repeat and "from" in filters and "to" in filters:
            self.search_params[chat_ID] = {
                "mode": "date_range",
                "from_date": filters["from"][:10]
            }
            self.bot.sendMessage(chat_ID, "📝 Enter new end date (DD-MM-YYYY), type 'edit start' to change start date, or 'exit' to stop:")

        elif chat_ID in self.authenticated_users:
            if "plate" in filters:
                self.search_params[chat_ID] = {"mode": "plate"}
                self.bot.sendMessage(chat_ID, "🔁 Enter another license plate or type 'exit' to stop:")
            elif "station" in filters:
                self.search_params[chat_ID] = {"mode": "semaphore"}
                self.bot.sendMessage(chat_ID, "🔁 Enter another semaphore ID or type 'exit' to stop:")
        else:
            self.search_params[chat_ID] = {"mode": "plate_only"}
            self.bot.sendMessage(chat_ID, "🔁 Enter another license plate or type 'exit' to stop:")

if __name__ == "__main__":
    info_path = "telegram_bot_info.json"
    resource_catalog_path = "resource_catalog_info.json"

    with open(info_path, "r") as f:
        info_data = json.load(f)

    config = info_data["config"][0]
    token = config['token']

    bot = MyBot(token, resource_catalog_path, info_path)
    threading.Thread(target=bot.register_to_catalog, daemon=True).start()

    print("Bot is running, access it from this link: https://t.me/Smart_Traffic_Lights_bot")

    while True:
        time.sleep(3)