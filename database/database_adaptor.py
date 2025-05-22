import cherrypy
import sqlite3
import json
import time
import threading
import requests
import os
from urllib.parse import parse_qs

# Dynamically set the database path
script_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(script_dir, "infraction_database.db")

@cherrypy.tools.json_out()
class DatabaseAdaptor:
    exposed = True

    def __init__(self, resource_info_path, catalog_info_path):
        self.init_db()

        # use absolute paths
        script_dir = os.path.dirname(os.path.abspath(__file__))
        resource_info_path = os.path.join(script_dir, resource_info_path)
        catalog_info_path = os.path.join(script_dir, catalog_info_path)

        # load JSON files
        self.resource_info = json.load(open(resource_info_path))
        catalog_info = json.load(open(catalog_info_path))
        self.catalog_url = f"http://{catalog_info['ip_address']}:{catalog_info['ip_port']}/registerResource"

        # start registration thread
        threading.Thread(target=self.register_to_catalog, daemon=True).start()

    def register_to_catalog(self):
        """ Periodically register this service to the catalog """
        while True:
            try:
                self.resource_info["lastUpdate"] = time.time()
                print(f"Registering: {self.resource_info['ID']}")
                response = requests.put(self.catalog_url, json=self.resource_info)
                print(f"Registered to catalog: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"Registration error: {e}")
            time.sleep(10)

    def init_db(self):
        """ Initializes the database table if it does not exist. """
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS violations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plate TEXT NOT NULL,
                    date TEXT NOT NULL,
                    station INTEGER NOT NULL
                )
            ''')
            conn.commit()

    def get_connection(self):
        return sqlite3.connect(DB_PATH, check_same_thread=False)

    def build_query(self, plate=None, station=None, from_date=None, to_date=None):
        query = "SELECT * FROM violations WHERE 1=1"
        params = []

        if plate:
            query += " AND plate = ?"
            params.append(plate)

        if station:
            query += " AND station = ?"
            params.append(station)

        if from_date and to_date:
            try:
                query += " AND CAST(date AS REAL) BETWEEN ? AND ?"
                params.extend([float(from_date), float(to_date)])
            except Exception as e:
                print(f"[ERROR] Invalid timestamp format: {e}")

        return query, params

    exposed = True

    def GET(self, **kwargs):
        params = {k: v[0] for k, v in parse_qs(cherrypy.request.query_string).items()}
        plate = params.get('plate')
        station = params.get('station')
        from_date = params.get('from')
        to_date = params.get('to')

        query, query_params = self.build_query(plate, station, from_date, to_date)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, query_params)
            results = cursor.fetchall()

        return [
            {"id": row[0], "plate": row[1], "date": row[2], "station": row[3]}
            for row in results
        ]

    def POST(self):
        try:
            raw_body = cherrypy.request.body.read().decode("utf-8")
            data = json.loads(raw_body)

            plate = data.get("plate")
            date = data.get("date")
            station = data.get("station")

            if not plate or not date or station is None:
                cherrypy.response.status = 400
                return {"error": "Missing required fields: plate, date, or station"}

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO violations (plate, date, station)
                    VALUES (?, ?, ?)
                ''', (plate, date, station))
                conn.commit()

            cherrypy.response.status = 201
            return {"message": "Violation added successfully!"}

        except json.JSONDecodeError:
            cherrypy.response.status = 400
            return {"error": "Invalid JSON format"}

        except Exception as e:
            cherrypy.response.status = 500
            return {"error": f"Internal Server Error: {e}"}


if __name__ == '__main__':
    resource_catalog_info_path = "resource_catalog_info.json"
    
    cherrypy.config.update({
        'server.socket_host': '0.0.0.0',
        'server.socket_port': 8080
    })

    cherrypy.quickstart(
        DatabaseAdaptor("database_adaptor_info.json", resource_catalog_info_path),
        '/infraction',
        {
            '/': {
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                'tools.response_headers.on': True,
                'tools.response_headers.headers': [('Content-Type', 'application/json')],
            }
        }
    )

