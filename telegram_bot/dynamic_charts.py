import requests
import matplotlib.pyplot as plt
from datetime import datetime
import matplotlib.dates as mdates
import os
import json
from dotenv import load_dotenv
load_dotenv('/app/.env')

thingspeak_api_key = os.getenv("THINGSPEAK_READ_KEY")
channel_id = os.getenv("THINGSPEAK_CHANNEL_ID")

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