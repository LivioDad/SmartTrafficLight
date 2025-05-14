import requests
import matplotlib.pyplot as plt
from datetime import datetime

def fetch_thingspeak_data(api_key, field, results=200):
    url = f"https://api.thingspeak.com/channels/2875299/fields/{field}.json?api_key={api_key}&results={results}"
    r = requests.get(url)
    r.raise_for_status()
    return r.json()["feeds"]

def generate_chart(api_key, field, ylabel, filename):
    feeds = fetch_thingspeak_data(api_key, field)
    x = [datetime.strptime(f["created_at"], "%Y-%m-%dT%H:%M:%SZ") for f in feeds if f.get(f"field{field}")]
    y = [float(f[f"field{field}"]) for f in feeds if f.get(f"field{field}")]

    plt.figure()
    plt.plot(x, y, marker='o', linestyle='-', color='red')
    plt.title(f"{ylabel} over Time")
    plt.xlabel("Date")
    plt.ylabel(ylabel)
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
