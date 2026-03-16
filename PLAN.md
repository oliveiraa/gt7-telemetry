# GT7 Telemetry & Analysis Hub - Development Plan

## Vision
Transform the current prototype into a standalone, automated racing telemetry hub. It will run silently in the background, automatically detect when a driving session starts, identify the track and car, and save structured data. Post-race, it will provide insights into racing lines, braking points, and consistency to help you find lap time.

---

## 1. Architecture Redesign

### The Ingestion Engine (State Machine)
Currently, we blindly write every packet to a single CSV. We need a "State Machine" that understands what the game is doing:
- **IDLE State:** Telemetry shows `is_paused`, `is_loading`, or `cars_on_track = False`. The engine ignores data.
- **SESSION_START State:** The car is on track and moving. A new session record is created.
- **TRACK_DETECT State:** During Lap 1, the engine tracks X/Z bounds and runs the Intersection over Union (IoU) algorithm to figure out the track. Once found, it locks the track name into the session metadata.
- **RECORDING State:** Actively saving high-fidelity telemetry (position, pedals, speed, RPM, suspension) tagged by Lap Number.
- **SESSION_END State:** The car enters the pits or returns to the menu. The engine closes the file and triggers the analysis pipeline.

### Storage Strategy: SQLite instead of CSV
While CSV is easy, querying 60 frames-per-second data across multiple laps gets messy. Moving to a lightweight **SQLite database** will allow us to instantly query things like:
* *"Give me the throttle data for Lap 4 where track distance > 1000m"*
* *"Compare my Top Speed on the main straight between Session A and Session B"*

---

## 2. Implementation Phases

### Phase 1: The Automated Session Manager
*   **Goal:** Set up the smart recording layer.
*   **Tasks:**
    *   [x] Implement the session state machine (detecting Menus vs. Driving).
    *   [x] Port the `gt7trackdetect` logic into our main python server so it automatically figures out the track without user input.
    *   [x] Change the storage backend to SQLite, saving files as `sessions/YYYYMMDD_HHMM_<Track>_<Car>.db`.
    *   [ ] Ensure the system can run as a background service on your Mac, requiring zero terminal commands once set up.
*   **Learnings & Notes:**
    *   **Data Integrity:** Moving to SQLite provides massive benefits. We use an auto-incrementing ID per session instead of throwing everything into one CSV. 
    *   **State Machine:** Checking `telemetry.cars_on_track`, `is_paused`, and `is_loading` correctly isolates active racing from menu navigation.
    *   **Track Detection:** The port of the IoU algorithm checks intersections efficiently. It builds a bounding box on Lap 1 and identifies the track ID accurately once crossed.
    *   **Async Operations:** Fastapi's loop easily handles running the WebSocket broadcast and the DB background recording concurrently at 20 frames per second.

### Phase 2: The Live Dashboard V2
*   **Goal:** Make the real-time UI actually useful while driving.
*   **Tasks:**
    *   [x] Add a Live Track Map that draws the circuit dynamically as you drive.
    *   [x] Display accurate Sector Times and Lap Deltas (Green/Red times).
    *   [x] Include a Tire Wear / Temperature degradation graph to know when tires are falling off.
*   **Learnings & Notes:**
    *   **HTML Canvas:** The most performant way to draw a live map without stutter is using native HTML5 Canvas.
    *   **Aspect Ratio Scaling:** Because coordinates change continuously on Lap 1, the canvas needs to dynamically scale the X/Z points to fit the width/height of the container while maintaining a strict 1:1 aspect ratio so the track doesn't look stretched or squished.
    *   **Live Timers:** The game doesn't send "current lap time", so it must be calculated client-side by tracking the delta of `time_of_day_ms` between ticks.
    *   **Chart.js Integration:** Adding a rolling line chart using Chart.js creates a beautiful historical view of tire temperature degradation. Limiting chart updates to 10 FPS (instead of 20) keeps the UI buttery smooth while driving.

### Phase 3: The Post-Race Driving Analyzer
*   **Goal:** Unlocking pace through data.
*   **Tasks:**
    *   [x] Create an "Analysis" tab on the web server.
    *   [x] **Pace Comparison:** Overlay your fastest lap against your average lap on a line graph (Speed vs. Distance).
    *   [x] **Brake Point Analysis:** Map visualization (like our prototype) showing exactly where you hit the brakes, identifying if you are braking too early or trailing off the brake incorrectly.
    *   [ ] **Corner Minimum Speeds (V-Min):** Automatically highlight corners where you carried the most/least speed.
*   **Learnings & Notes:**
    *   **Distance Calculation:** Since telemetry doesn't provide a "distance travelled" metric natively, I calculated the 3D Pythagorean distance between sequential X/Y/Z points to generate an accurate X-axis for plotting line graphs.
    *   **Plotly:** Using Plotly.js on the frontend enables incredibly smooth zooming and panning over high-density telemetry data without lagging the browser.
    *   **Data Aggregation:** The sqlite backend quickly groups and delivers lap-by-lap arrays, making the frontend rendering almost instantaneous.

---

## 3. Tech Stack
*   **Backend:** Python 3 + FastAPI + `gt_telem` (Handles data capture and API endpoints)
*   **Database:** SQLite + SQLAlchemy (Local, zero-config, highly queryable)
*   **Frontend (Live):** HTML/JS with WebSockets (Ultra-low latency for live driving)
*   **Frontend (Analysis):** Plotly.js or Chart.js (Interactive, zoomable charts for post-race data)
