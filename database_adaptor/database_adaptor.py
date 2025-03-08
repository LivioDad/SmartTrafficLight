import cherrypy
import sqlite3
import json
from urllib.parse import parse_qs

DB_PATH = "infraction_database.db"

class DatabaseAdaptor:
    
    def __init__(self):
        self.init_db()

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
        """ Returns a new database connection. """
        return sqlite3.connect(DB_PATH)
    
    def build_query(self, plate=None, station=None, from_date=None, to_date=None):
        """ Builds a dynamic SQL query based on the given parameters. """
        
        query = "SELECT * FROM violations WHERE 1=1"
        params = []

        if plate:
            query += " AND plate = ?"
            params.append(plate)

        if station:
            query += " AND station = ?"
            params.append(station)

        if from_date and to_date:
            query += " AND date BETWEEN ? AND ?"
            params.extend([from_date, to_date])
        
        return query, params
    
    expose = True

    def GET(self, **kwargs):
        """ Handles GET requests for retrieving infractions based on filters. 
            kwargs = {
                        "plate": "AB123CD",
                        "station": "15",
                        "from": "2025-03-01",
                        "to": "2025-03-05"
                    }
        """
        
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
        """ Add new violations to the database. """
        try:
            # Parse JSON body
            raw_body = cherrypy.request.body.read().decode("utf-8")
            data = json.loads(raw_body)

            # Extract fields
            plate = data.get("plate")
            date = data.get("date")
            station = data.get("station")

            # Validate input fields
            if not plate or not date or not station:
                cherrypy.response.status = 400
                return {"error": "Missing required fields: plate, date, or station"}

            # Insert into database
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO violations (plate, date, station)
                    VALUES (?, ?, ?)
                ''', (plate, date, station))
                conn.commit()

            # Return success response
            cherrypy.response.status = 201
            return {"message": "Violation added successfully!"}

        except json.JSONDecodeError:
            cherrypy.response.status = 400
            return {"error": "Invalid JSON format"}

        except Exception as e:
            cherrypy.response.status = 500
            return {"error": f"Internal Server Error: {e}"}
    

if __name__ == '__main__':
    cherrypy.quickstart(DatabaseAdaptor(), '/', {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'application/json')],
        }
    })
