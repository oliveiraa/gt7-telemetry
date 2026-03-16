import sqlite3
import os
from datetime import datetime
from track_detector import TrackDetector

class SessionManager:
    def __init__(self, db_dir="data/sessions", cars_db=None):
        self.db_dir = db_dir
        self.cars_db = cars_db or {}
        self.state = "IDLE"
        self.conn = None
        self.cursor = None
        self.session_id = None
        self.track_detector = TrackDetector("gt7trackdetect.csv")
        self.prev_lap = -1
        self.track_detected = False
        self.start_time = None
        self.car_name = "Unknown"
        self.track_id = -1
        self.track_name = "Unknown"
        self.last_time_ms = 0

        if not os.path.exists(self.db_dir):
            os.makedirs(self.db_dir)

    def process(self, telemetry):
        if telemetry is None:
            return

        # If we are completely out of a race or loading
        if not telemetry.cars_on_track or telemetry.is_loading:
            if self.state != "IDLE":
                self._end_session()
                self.state = "IDLE"
            return

        # Check for Retry (lap went backwards, or time reset significantly)
        if self.state in ["RECORDING", "PAUSED"]:
            time_jumped_back = False
            # If the current in-game time is somehow much less than our last recorded time, it's a restart
            if telemetry.time_of_day_ms < self.last_time_ms - 5000:
                time_jumped_back = True
            
            # If lap count drops, it's definitely a restart
            if telemetry.current_lap > 0 and telemetry.current_lap < self.prev_lap:
                time_jumped_back = True
                
            if time_jumped_back:
                print("Race Retry detected! Resetting session...")
                self._end_session()
                self.state = "IDLE"

        self.last_time_ms = telemetry.time_of_day_ms

        # State transitions
        if self.state == "IDLE":
            if telemetry.current_lap > 0 and not telemetry.is_paused:
                self._start_session(telemetry)
                self.state = "RECORDING"
        
        elif self.state == "RECORDING":
            if telemetry.is_paused:
                self.state = "PAUSED"
                print("Race Paused. Suspending recording...")
            else:
                self._record_telemetry(telemetry)
                self._handle_track_detection(telemetry)
                self.prev_lap = telemetry.current_lap
                
        elif self.state == "PAUSED":
            if not telemetry.is_paused:
                self.state = "RECORDING"
                print("Race Resumed. Continuing recording...")

    def _start_session(self, telemetry):
        self.start_time = datetime.now()
        timestamp_str = self.start_time.strftime("%Y%m%d_%H%M%S")
        self.car_name = self.cars_db.get(telemetry.car_code, "Unknown")
        safe_car_name = "".join([c if c.isalnum() else "_" for c in self.car_name]).strip("_")
        
        db_filename = f"{timestamp_str}_UnknownTrack_{safe_car_name}.db"
        self.db_path = os.path.join(self.db_dir, db_filename)
        
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # Create schema
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT,
                end_time TEXT,
                track_id INTEGER,
                track_name TEXT,
                car_code INTEGER,
                car_name TEXT
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                timestamp TEXT,
                lap INTEGER,
                position_x REAL,
                position_y REAL,
                position_z REAL,
                velocity_x REAL,
                velocity_y REAL,
                velocity_z REAL,
                speed_mps REAL,
                throttle REAL,
                brake REAL,
                gear INTEGER,
                engine_rpm REAL,
                tire_fl_temp REAL,
                tire_fr_temp REAL,
                tire_rl_temp REAL,
                tire_rr_temp REAL,
                tire_fl_sus_height REAL,
                tire_fr_sus_height REAL,
                tire_rl_sus_height REAL,
                tire_rr_sus_height REAL
            )
        ''')
        
        self.cursor.execute('''
            INSERT INTO sessions (start_time, car_code, car_name, track_name) 
            VALUES (?, ?, ?, ?)
        ''', (self.start_time.isoformat(), telemetry.car_code, self.car_name, self.track_name))
        self.session_id = self.cursor.lastrowid
        self.conn.commit()

        self.track_detector.reset()
        self.track_detected = False
        self.prev_lap = telemetry.current_lap
        print(f"Started new recording session: {db_filename}")

    def _end_session(self):
        if self.conn:
            end_time = datetime.now().isoformat()
            self.cursor.execute('UPDATE sessions SET end_time = ? WHERE id = ?', (end_time, self.session_id))
            self.conn.commit()
            self.conn.close()
            self.conn = None
            print("Ended recording session.")

    def _record_telemetry(self, t):
        self.cursor.execute('''
            INSERT INTO telemetry (
                session_id, timestamp, lap, position_x, position_y, position_z, 
                velocity_x, velocity_y, velocity_z, speed_mps, throttle, brake, gear, 
                engine_rpm, tire_fl_temp, tire_fr_temp, tire_rl_temp, tire_rr_temp,
                tire_fl_sus_height, tire_fr_sus_height, tire_rl_sus_height, tire_rr_sus_height
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            self.session_id, datetime.now().isoformat(), t.current_lap, 
            t.position.x, t.position.y, t.position.z,
            t.velocity.x, t.velocity.y, t.velocity.z,
            t.speed_mps, t.throttle, t.brake, t.current_gear,
            t.engine_rpm, t.tire_temp.fl, t.tire_temp.fr, t.tire_temp.rl, t.tire_temp.rr,
            t.suspension_height.fl, t.suspension_height.fr, t.suspension_height.rl, t.suspension_height.rr
        ))

    def _handle_track_detection(self, t):
        if self.track_detected:
            return

        x = t.position.x
        z = t.position.z
        
        self.track_detector.update_bounds(x, z)
        
        if t.current_lap > self.prev_lap:
            self.prev_lap = t.current_lap
            detected_track_id = self.track_detector.detect_track(x, z)
            
            if detected_track_id:
                self.track_id = detected_track_id
                self.track_name = f"Track_{detected_track_id}"  # You can expand this to look up a track names CSV
                self.track_detected = True
                
                # Update session DB
                self.cursor.execute('UPDATE sessions SET track_id = ?, track_name = ? WHERE id = ?', 
                                  (self.track_id, self.track_name, self.session_id))
                self.conn.commit()
                print(f"Track Detected! ID: {self.track_id}")
                
                # Rename file to include track name
                new_filename = f"{self.start_time.strftime('%Y%m%d_%H%M%S')}_{self.track_name}_{''.join([c if c.isalnum() else '_' for c in self.car_name]).strip('_')}.db"
                new_path = os.path.join(self.db_dir, new_filename)
                
                self.conn.close()
                os.rename(self.db_path, new_path)
                self.db_path = new_path
                self.conn = sqlite3.connect(self.db_path)
                self.cursor = self.conn.cursor()
