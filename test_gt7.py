import json
from gt_telem import TurismoClient
import time
import argparse

def main():
    parser = argparse.ArgumentParser(description="Capture GT7 Telemetry")
    parser.add_argument("--ip", type=str, required=True, help="IP address of PlayStation")
    args = parser.parse_args()

    print(f"Connecting to Gran Turismo 7 on {args.ip}...")
    tc = TurismoClient(args.ip)
    
    # Start the client thread
    tc.start()
    
    print("Waiting for telemetry (Ensure GT7 is running and telemetry is enabled)...")
    try:
        samples_collected = 0
        while samples_collected < 5:
            if tc.telemetry:
                # tc.telemetry is likely an object or dictionary. We'll try to convert to dict or print it.
                if hasattr(tc.telemetry, 'to_dict'):
                    data = tc.telemetry.to_dict()
                else:
                    data = str(tc.telemetry)
                
                print(f"--- Sample {samples_collected + 1} ---")
                print(data)
                samples_collected += 1
            time.sleep(1)
            
        print("Successfully captured data. Shutting down...")
    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        tc.stop()

if __name__ == "__main__":
    main()
