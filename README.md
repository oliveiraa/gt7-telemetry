# GT7 Telemetry & Analysis Hub

A fully automated, real-time telemetry dashboard and post-race analysis tool for Gran Turismo 7.

This application connects to your PlayStation console over your local network to capture real-time telemetry from Gran Turismo 7. It provides a live browser-based dashboard while you drive, and silently records your session data into an SQLite database. After your race, you can use the built-in Analyzer to review your racing lines, braking points, and lap-by-lap pace.

## Features

*   **Live Dashboard:** Real-time visualization of your Speed, Gear, RPM, Pedal Inputs (Throttle/Brake/Clutch), Lap Times, and Tire Temperatures.
*   **Live Track Map:** Automatically draws the circuit geometry dynamically as you drive your first lap.
*   **Automated Session Manager:** The backend "State Machine" knows when you are racing vs. when you are in the menus. It automatically starts and stops recording sessions to SQLite without manual intervention.
*   **Smart Track Detection:** Implements a geometric *Intersection over Union (IoU)* algorithm to automatically detect which track you are racing on without any user input.
*   **Post-Race Analyzer:** Interactive, zoomable charts (powered by Plotly) to analyze your speed vs. distance, pedal inputs, and a color-coded top-down view of your racing line and braking zones.

## Prerequisites

1.  A PlayStation 4 or PlayStation 5 running Gran Turismo 7.
2.  A PC, Mac, or Raspberry Pi connected to the **same local network** as your PlayStation.
3.  Python 3.9 or newer.

## Installation

1. Clone this repository:
```bash
git clone https://github.com/oliveiraa/gt7-telemetry.git
cd gt7-telemetry
```

2. Create a virtual environment and install the dependencies:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
pip install -r requirements.txt
```

3. Configure your PlayStation IP:
Find your PlayStation's IP Address in its network settings. Open `server.py` and update the `IP_ADDRESS` variable at the top of the file:
```python
IP_ADDRESS = "192.168.1.XXX" # Replace with your console's IP
```

## Usage

1. Start the backend server:
```bash
source venv/bin/activate
python server.py
```

2. Open your web browser (on any device on your network, like your phone or tablet) and navigate to:
```
http://localhost:8000
```
*(If accessing from another device, replace `localhost` with the IP address of the computer running the server, e.g., `http://192.168.1.50:8000`)*

3. Start driving in Gran Turismo 7! The dashboard will light up, and the background Session Manager will automatically begin logging your data.

4. When you are done racing, click **"Post-Race Analysis →"** in the top right corner of the dashboard to view your interactive telemetry graphs.

## Credits & Acknowledgements

*   This project relies on the fantastic [gt-telem](https://github.com/RaceCrewAI/gt-telem) library for protocol decryption.
*   Track detection database and methodology inspired by the work of [Bornhall](https://github.com/Bornhall/gt7telemetry) and the GTPlanet community.
