import asyncio
import os
import csv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from gt_telem import TurismoClient
import uvicorn
from contextlib import asynccontextmanager
from session_manager import SessionManager

IP_ADDRESS = "192.168.1.230"
tc = None
cars_db = {}
session_manager = None

def load_cars():
    global cars_db
    try:
        with open("db/cars.csv", "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader) # skip header
            for row in reader:
                if len(row) >= 2:
                    cars_db[int(row[0])] = row[1]
    except Exception as e:
        print(f"Could not load cars.csv: {e}")

async def telemetry_loop():
    global tc, session_manager
    while True:
        if tc and getattr(tc, 'telemetry', None):
            session_manager.process(tc.telemetry)
        await asyncio.sleep(0.05)  # 20 FPS

@asynccontextmanager
async def lifespan(app: FastAPI):
    global tc, session_manager
    load_cars()
    
    session_manager = SessionManager(cars_db=cars_db)
    
    print(f"Connecting to GT7 at {IP_ADDRESS}...")
    tc = TurismoClient(IP_ADDRESS)
    tc.start()
    
    # Start the background telemetry processing loop
    task = asyncio.create_task(telemetry_loop())
    
    yield
    
    task.cancel()
    if tc:
        tc.stop()
        print("Disconnected from GT7.")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import math
import sqlite3

@app.get("/")
async def get():
    with open(os.path.join(os.path.dirname(__file__), "index.html"), "r") as f:
        html_content = f.read()
    return HTMLResponse(html_content)

@app.get("/analysis")
async def get_analysis():
    with open(os.path.join(os.path.dirname(__file__), "analysis.html"), "r") as f:
        html_content = f.read()
    return HTMLResponse(html_content)

@app.get("/api/sessions")
async def list_sessions():
    sessions = []
    db_dir = "data/sessions"
    if not os.path.exists(db_dir):
        return []
    
    for filename in os.listdir(db_dir):
        if filename.endswith(".db"):
            try:
                conn = sqlite3.connect(os.path.join(db_dir, filename))
                cursor = conn.cursor()
                cursor.execute("SELECT id, start_time, track_name, car_name FROM sessions ORDER BY id DESC LIMIT 1")
                row = cursor.fetchone()
                if row:
                    sessions.append({
                        "file": filename,
                        "id": row[0],
                        "start_time": row[1],
                        "track_name": row[2],
                        "car_name": row[3]
                    })
                conn.close()
            except Exception as e:
                print(f"Error reading session {filename}: {e}")
                
    # Sort newest first
    sessions.sort(key=lambda x: x["start_time"], reverse=True)
    return sessions

@app.get("/api/analyze")
async def analyze_session(file: str):
    db_path = os.path.join("data/sessions", file)
    if not os.path.exists(db_path):
        return {"error": "File not found"}
        
    conn = sqlite3.connect(db_path)
    # We want to group data by lap and calculate distance traveled per lap
    
    cursor = conn.cursor()
    # Get distinct laps
    cursor.execute("SELECT DISTINCT lap FROM telemetry WHERE lap > 0 ORDER BY lap")
    laps = [row[0] for row in cursor.fetchall()]
    
    lap_data = []
    
    for lap in laps:
        cursor.execute("""
            SELECT position_x, position_y, position_z, speed_mps, throttle, brake, timestamp 
            FROM telemetry 
            WHERE lap = ? 
            ORDER BY id ASC
        """, (lap,))
        rows = cursor.fetchall()
        
        if len(rows) < 10: # Skip incomplete laps
            continue
            
        distances = []
        speeds = []
        throttles = []
        brakes = []
        pos_x = []
        pos_z = []
        
        total_dist = 0.0
        prev_x, prev_y, prev_z = rows[0][0], rows[0][1], rows[0][2]
        
        for row in rows:
            x, y, z, speed, t, b, _ = row
            
            # Calculate 3D distance between points
            dist = math.sqrt((x-prev_x)**2 + (y-prev_y)**2 + (z-prev_z)**2)
            total_dist += dist
            
            distances.append(total_dist)
            speeds.append(speed * 3.6) # convert m/s to km/h
            throttles.append((t / 255.0) * 100.0) # 0-100%
            brakes.append((b / 255.0) * 100.0) # 0-100%
            pos_x.append(x)
            pos_z.append(z)
            
            prev_x, prev_y, prev_z = x, y, z
            
        # Very rough approximation of lap time (we could also pull from DB if we logged it)
        # For now, just flag the fastest lap by average speed
        avg_speed = sum(speeds) / len(speeds)
            
        lap_data.append({
            "lap_number": lap,
            "distance": distances,
            "speed": speeds,
            "throttle": throttles,
            "brake": brakes,
            "pos_x": pos_x,
            "pos_z": pos_z,
            "avg_speed": avg_speed,
            "is_fastest": False
        })
        
    conn.close()
    
    if lap_data:
        fastest = max(lap_data, key=lambda l: l["avg_speed"])
        fastest["is_fastest"] = True
        
    return {"laps": lap_data}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("New websocket client connected.")
    try:
        while True:
            if tc and getattr(tc, 'telemetry', None):
                data = {}
                for key in dir(tc.telemetry):
                    if not key.startswith("_"):
                        try:
                            val = getattr(tc.telemetry, key)
                            if not callable(val) and isinstance(val, (int, float, str, bool, type(None))):
                                data[key] = val
                        except Exception:
                            pass
                
                # Add human-readable car name
                if 'car_code' in data and data['car_code'] in cars_db:
                    data['car_name'] = cars_db[data['car_code']]
                else:
                    data['car_name'] = "Unknown"

                # Send live track info if detected
                if session_manager.track_detected:
                    data['track_name'] = session_manager.track_name

                await websocket.send_json(data)
            await asyncio.sleep(0.05)  # 20 FPS updates
    except WebSocketDisconnect:
        print("Websocket client disconnected")
    except Exception as e:
        print(f"Websocket error: {e}")

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, log_level="info", ws="wsproto")
