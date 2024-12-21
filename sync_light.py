import argparse
import time
import subprocess
import os

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Update smart bulbs with rotary value brightness and on/off state.")
parser.add_argument("--file", type=str, required=True, help="Path to the rotary value output file.")
parser.add_argument("--bulbs", type=str, nargs='+', required=True, help="List of smart bulb IP addresses.")
args = parser.parse_args()

# Global flag to track if the latest update has been sent
in_sync = True

# Function to set brightness using python-kasa
def set_brightness(ip, brightness):
    try:
        command = ["kasa", "--host", ip, "brightness", str(brightness)]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[INFO] Successfully updated bulb {ip} to brightness {brightness}.")
        else:
            print(f"[ERROR] Failed to update bulb {ip}: {result.stderr}")
    except Exception as e:
        print(f"[ERROR] Exception while updating bulb {ip}: {e}")

# Function to turn bulb on or off using python-kasa
def set_power(ip, power_on):
    try:
        command = ["kasa", "--host", ip, "on" if power_on else "off"]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            state = "ON" if power_on else "OFF"
            print(f"[INFO] Successfully turned {state} bulb {ip}.")
        else:
            print(f"[ERROR] Failed to set power state for bulb {ip}: {result.stderr}")
    except Exception as e:
        print(f"[ERROR] Exception while setting power state for bulb {ip}: {e}")

# Function to read and validate the latest rotary value and state from the file
def read_latest_value(file_path):
    try:
        with open(file_path, "r") as file:
            lines = file.readlines()
            if lines:
                last_line = lines[-1].strip()
                parts = last_line.split(";")

                # Validate the format
                if len(parts) == 2 and parts[0].isdigit() and parts[1] in {"0", "1"}:
                    return int(parts[0]), int(parts[1])

                print(f"[WARN] Invalid line format in file: {last_line}")
    except Exception as e:
        print(f"[ERROR] Could not read from file {file_path}: {e}")
    return None, None

# Main loop
try:
    print(f"[INFO] Starting lightbulb updater, watching for changes in {args.file}.")
    print(f"[INFO] Updating bulbs: {', '.join(args.bulbs)}")

    last_mod_time = 0
    last_update_time = 0

    while True:
        try:
            current_mod_time = os.path.getmtime(args.file)

            # If the file has been modified, mark as out of sync
            if current_mod_time != last_mod_time:
                last_mod_time = current_mod_time
                in_sync = False
                last_update_time = time.time()

            # Check if it's time to send an update
            if not in_sync and (time.time() - last_update_time) > 1:  # 1000ms threshold
                # Read the latest rotary value and on/off state
                latest_brightness, power_state = read_latest_value(args.file)

                if latest_brightness is not None and power_state is not None:
                    # Clamp the brightness value to 1-100 (brightness of 1 when off assumed)
                    brightness = max(1, min(100, latest_brightness)) if power_state else 1

                    # Update all bulbs
                    for bulb_ip in args.bulbs:
                        set_power(bulb_ip, power_state)
                        if power_state:  # Only set brightness if the bulb is on
                            set_brightness(bulb_ip, brightness)

                    # Mark as in sync
                    in_sync = True
                else:
                    print("[WARN] No valid rotary value or power state found, skipping this update.")

            time.sleep(0.1)  # Check for updates frequently without excessive CPU usage

        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            time.sleep(1)

except KeyboardInterrupt:
    print("[INFO] Exiting lightbulb updater.")
