# SmartTrafficLight

**SmartTrafficLight** is a modular, scalable, and IoT-based system for managing smart traffic intersections with real-time monitoring, infraction detection, and environmental responsiveness.

---

## 🌐 Overview

This system simulates and manages a network of smart semaphores using:

* **Raspberry Pi + GPIO** for physical signals (LEDs, sensors)
* **MQTT** for communication
* **Docker** for modular microservices
* **SQLite** for storing infractions and registered semaphores
* **Python** as the main scripting language

> ⚠️ **Important:** Scripts that interact with GPIO (e.g. for LEDs and sensors) are **not containerized**. This is due to hardware access restrictions inside Docker: GPIO interfaces require direct access to `/dev/gpiomem` and other host-level resources, which are not straightforward to expose safely or portably within containers. As a result, all GPIO-based scripts are executed directly on the host system.

---

## 🚧 Features

* Dynamic traffic light control (standard/emergency/pedestrian/vulnerable)
* Environmental response (e.g. ice risk via sensor simulation)
* Vehicle infraction detection (e.g. passing on red)
* Real-time display via LCD
* Telegram bot integration for remote queries and reports
* Dynamic semaphore creation via terminal interface

---

## 📡 IoT Communication Protocols

The SmartTrafficLight system is based on a distributed edge architecture where each node (traffic light, sensor, actuator) communicates using standard IoT protocols.

### 🔄 MQTT (Message Queuing Telemetry Transport)

- Used for lightweight, asynchronous communication between modules.
- Managed via a central MQTT broker whose address is dynamically obtained from the `resource_catalog`.
- Topics follow a structured hierarchy:
  ```
  SmartTrafficLight/<category>/<zone>/<event>
  ```

#### 📤 Main Publishers
| Module | Event Published |
|--------|------------------|
| `Button.py` | pedestrian button pressed |
| `PIR.py` | motion detected |
| `DHT22.py` | temperature and humidity |
| `infraction_sensor.py` | traffic violation |
| `led_manager.py` | command messages to traffic lights (mode, duration, etc.) |

#### 📥 Main Subscribers
| Module | Topic Subscribed |
|--------|------------------|
| `led_manager.py` | listens to events from sensors, buttons, simulations |
| `Semaphore_X.py` | listens to commands and ice warnings |
| `ThingSpeak_Adaptor.py` | listens to sensor measurements |
| `violation_detection.py` | listens to violation data |

---

### 🌐 HTTP

- Used for node registration and broker discovery.
- Each module performs:
  - `GET /broker` → to retrieve the broker IP/port
  - `PUT /registerResource` → to register itself to the catalog

#### 🔁 HTTP Usage Summary
| Module | Purpose |
|--------|---------|
| All edge modules (e.g., `Button.py`, `DHT22.py`, `Semaphore_1.py`) | retrieve broker and register to catalog |
| `database_adaptor.py` | receives data via HTTP POST |
| `ThingSpeak_Adaptor.py` | pushes sensor data to ThingSpeak via HTTP POST |

---

### 🧠 Edge-Distributed Architecture

Each traffic light node:
- subscribes to MQTT commands
- processes logic autonomously
- updates its state independently

This ensures:
- ⚡ Low latency
- 🔁 High resilience to disconnections
- 🧩 Modular scalability

---

## 📂 Project Structure

```
SmartTrafficLight/
├── database/               # SQLite DB file (database.db)
├── Semaphores/             # Semaphore_X.py + info.json
├── Sensors/                # DHT22, PIR, Button
├── violation_detection/    # Infraction sensor
├── services/               # Simulated services (e.g. ice risk)
├── LedManager/             # Emergency simulator
├── shared/                 # Shared MQTT catalog info
├── start_system.sh         # Main launcher with interactive menu
├── stop_system.sh          # Stop all scripts and Docker
├── add_semaphore.py        # Add new semaphore from terminal
├── docker-compose.yml      # Services: resource_catalog, database_adaptor, telegram_bot
```
---

## ⚖️ Requirements

* Raspberry Pi5 with GPIO
* Python 3.8+
* Docker + Docker Compose
* Packages:

  * `gpiozero`, `paho-mqtt`, `requests`, `sqlite3`, `cherrypy`, `lgpio`, `adafruit-circuitpython-dht`, `blinka`

The installation is automatically done at start, but you can run the installation separately via:

```bash
./install_requirements.sh
```

---

## 🔄 Running the System

Remember to compile the .env file in the "shared" folder before starting the system!
After that, to launch everything:

```bash
./start_system.sh
```

This will:

1. Start Docker containers (resource\_catalog, database\_adaptor, telegram\_bot)
2. Start main sensors and semaphore scripts
3. Show interactive menu for optional components

To stop everything:

```bash
./stop_system.sh
```

---

## 🎓 Adding a New Semaphore

From the terminal:

```bash
python3 Semaphores/Add_semaphore.py
```

It will:

1. Ask for the zone (e.g. A)
2. Ask which services to activate (lcd, emergency, etc.)
3. Insert it into the database
4. Create `Semaphore_X.py` and `Semaphore_X_info.json`
5. Prompt you to manually set GPIO pins and duty cycles

---

## 📢 Telegram Bot

The system includes a **Telegram bot** for remote interaction:

* Query recent infractions by plate or zone
* Get real-time environment data from sensors (e.g. temperature, humidity)
* Export results as CSV

Once the system is started (`./start_system.sh`), the bot becomes accessible at:

**[https://t.me/Smart_Traffic_Lights_bot](https://t.me/Smart_Traffic_Lights_bot)**

> 📅 You can also scan the QR code below to open it directly in Telegram:

![QR Code to SmartTrafficLightBot](assets/telegram_qr_code.jpg)

---

## 📊 Catalog Service

The **resource catalog** (running in Docker) is a key component of service discovery in this system. Every script (sensor, actuator, or service) registers itself with the catalog by periodically sending a `PUT` request with its metadata. This enables dynamic discovery of available services and brokers by other components, reducing hard-coded configuration.

The catalog runs at `http://<host>:9090/` and stores all live services with their type, name, zone, IP, and topics.


---

## 📁 Database

* **File**: `database/database.db`
* **Tables**:

  * `violations`: stores infractions (plate, timestamp, station)
  * `semaphores`: stores semaphores with zone and active services (as JSON)

---

## ⚡ Tips

* Use `logs/` to debug any component. All scripts write to log files.
* Use `script_pids.txt` to stop manually any launched script.
* Use `Ctrl+C` inside menu-launched scripts to return to the menu.

---

## 📄 License

MIT License

---

## 🚀 Future Improvements

* Web dashboard for live monitoring
* Database migrations (e.g. with Alembic)
* Better GUI for Raspberry Pi interface
* Integration with cameras and OCR

---

## ✉️ Contact

For questions, suggestions, or contributions, open an issue or reach out to the authors:

- [**Giovanni Grieco**](mailto:s346012@studenti.polito.it)
- [**Livio Dadone**](mailto:s347038@studenti.polito.it)
- [**Mattia Antonini**](mailto:s344064@studenti.polito.it)
- [**Simone Peradotto**](mailto:s343420@studenti.polito.it)


---

Enjoy your smart traffic light system! 🚗🚦🛡️
