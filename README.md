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
* Telegram bot integration (not detailed here)
* Dynamic semaphore creation via terminal interface

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
├── docker-compose.yml      # Services: resource_catalog, database_adaptor
```

---

## 📁 Database

* **File**: `database/database.db`
* **Tables**:

  * `violations`: stores infractions (plate, timestamp, station)
  * `semaphores`: stores semaphores with zone and active services (as JSON)

---

## ⚖️ Requirements

* Raspberry Pi5 with GPIO (or simulation on desktop)
* Python 3.8+
* Docker + Docker Compose
* Packages:

  * `gpiozero`, `paho-mqtt`, `requests`, `sqlite3`, `cherrypy`, `lgpio`, `adafruit-circuitpython-dht`, `blinka`

The installation is automatically done at start, but you can separately install them via:

```bash
./install_requirements.sh
```

---

## 🔄 Running the System

To launch everything:

```bash
./start_system.sh
```

This will:

1. Start Docker containers (resource\_catalog, database\_adaptor)
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

## 🌐 Web Interface (Optional)

The `database_adaptor` exposes REST APIs on port `8080`:

* `GET /infraction`: query violations
* `POST /infraction`: add a violation

Example:

```bash
curl -X POST http://localhost:8080/infraction \
     -H "Content-Type: application/json" \
     -d '{"plate": "ABC123", "date": "1747990000", "station": 2}'
```

---

## 📊 Catalog Service

The **resource catalog** (running in Docker) is a key component of service discovery in this system. Every script (sensor, actuator, or service) registers itself with the catalog by periodically sending a `PUT` request with its metadata. This enables dynamic discovery of available services and brokers by other components, reducing hard-coded configuration.

The catalog runs at `http://<host>:9090/` and stores all live services with their type, name, zone, IP, and topics.

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

For questions, suggestions, or contributions, open an issue or contact the project maintainer on GitHub.

---

Enjoy your smart traffic light system! 🚗🚦🛡️