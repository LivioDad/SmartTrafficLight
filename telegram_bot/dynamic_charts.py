import requests
import matplotlib.pyplot as plt
from datetime import datetime
import matplotlib.dates as mdates
import os
import json

script_dir = os.path.dirname(os.path.abspath(__file__))
info_path = os.path.join(script_dir, "telegram_bot_info.json")

with open(info_path, "r") as f:
    info_data = json.load(f)

config = info_data["config"][0]
thingspeak_api_key = config.get("thingspeak_api_key", "")
channel_id = info_data["environment_zones"]["a"]["channel_id"] # For the moment it is only configured for zone A

def fetch_thingspeak_data(field, results=50):
    url = f"https://api.thingspeak.com/channels/{channel_id}/fields/{field}.json?api_key={thingspeak_api_key}&results={results}"
    r = requests.get(url)
    r.raise_for_status()
    return r.json()["feeds"]

def generate_chart(field, ylabel, filename, results=50):
    feeds = fetch_thingspeak_data(field, results=results)

    x = [datetime.strptime(f["created_at"], "%Y-%m-%dT%H:%M:%SZ") for f in feeds if f.get(f"field{field}")]
    y = [float(f[f"field{field}"]) for f in feeds if f.get(f"field{field}")]

    plt.figure()
    plt.plot(x, y, marker='o', linestyle='-', color='red')
    plt.title(f"{ylabel} over Time")
    plt.xlabel("Date")
    plt.ylabel(ylabel)
    plt.grid(True)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d-%m-%Y %H:%M'))
    plt.xticks(rotation=45)
    plt.gcf().autofmt_xdate()
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()