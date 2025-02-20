import evdev
from gpiozero import Motor
import logging
from datetime import datetime
import os
import subprocess
import json
import time
import threading

stop_search_event = threading.Event()


logging.basicConfig(filename='/home/pi/joystick.log', level=logging.DEBUG)
logging.debug('Motor control service started')

# GPIO pin setup for Motor Driver 1 (Motors A and B)
IN1_A = 17
IN2_A = 27
IN3_A = 22
IN4_A = 23
running_search = False
JSON_FILE_PATH = "/home/pi/frame_annotated/annotations.json"

def find_joystick_device():
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for device in devices:
        if "Nintendo Switch Pro Controller" == device.name:
            logging.debug(f"Joystick found: {device.name} at {device.path}")
            return device.path
    logging.debug("Joystick not found")
    return None


# Define motors
try:
    motor_a = Motor(forward=IN1_A, backward=IN2_A)
    motor_b = Motor(forward=IN3_A, backward=IN4_A)
    
    device_path = find_joystick_device()

    if device_path:
        logging.debug(f"Using device path: {device_path}")
    else:
        logging.debug("No joystick device found. Exiting...")
        exit(1)

except Exception as e:
    logging.debug(f"Error initializing motors or finding joystick: {e}")

left_y = 0
right_x = 0

STREAM_TO_HTTP = 305  #A
STREAM_TO_FILE = 304  #B
SEARCH_FOR_KNOTWEED = 307 #X

def normalize(value, min_value, max_value):
    normalized_value = (value - min_value) / (max_value - min_value) * 2 - 1
    return max(min(normalized_value, 1), -1)

def clamp(value, min_value=0, max_value=1):
    return max(min(value, max_value), min_value)

def control_tracks(left_y, right_x):
    try:
        norm_left_y = normalize(left_y, -32768, 32767)
        norm_right_x = normalize(right_x, -32768, 32767)

        if abs(norm_left_y) > 0.2:
            if norm_left_y > 0:
                if norm_right_x > 0:  # Turning left
                    norm_left_y_turn = norm_left_y - (norm_right_x * 0.9)
                    motor_a.forward(clamp(norm_left_y_turn))
                    motor_b.forward(clamp(norm_left_y))
                else:  # Turning right
                    norm_left_y_turn = norm_left_y + (norm_right_x * 0.9)
                    motor_a.forward(clamp(norm_left_y))
                    motor_b.forward(clamp(norm_left_y_turn))
            elif norm_left_y < 0:
                if norm_right_x > 0:
                    norm_left_y_turn = norm_left_y + (norm_right_x * 0.9)
                    motor_a.backward(clamp(-norm_left_y_turn))
                    motor_b.backward(clamp(-norm_left_y))
                else:
                    norm_left_y_turn = norm_left_y - (norm_right_x * 0.9)
                    motor_a.backward(clamp(-norm_left_y))
                    motor_b.backward(clamp(-norm_left_y_turn))
        else:
            stop_motors()
            norm_right_x = normalize(right_x, -32768, 32767)
            speed = 0.75 * norm_right_x
            if norm_right_x > 0:
                motor_a.forward(abs(speed))
                motor_b.backward(abs(speed))
            else:
                motor_a.backward(abs(speed))
                motor_b.forward(abs(speed))

    except Exception as e:
        logging.debug(f"Error in control_tracks: {e}")

def stop_motors():
    """Stops all motors and signals the knotweed search to stop."""
    try:
        motor_a.stop()
        motor_b.stop()
        stop_search_event.set()  # Signal search thread to stop
        logging.debug("All motors stopped. Search interrupted if running.")
    except Exception as e:
        logging.debug(f"Error stopping motors: {e}")


def handle_event(event):
    global left_y, right_x, running_search
    try:
        if event.type == evdev.ecodes.EV_ABS and running_search == False:
            logging.debug(f"event: {event.code}")
            if event.code == evdev.ecodes.ABS_Y:
                left_y = event.value
                logging.debug(f"Left Y-axis value: {left_y}")
            elif event.code == evdev.ecodes.ABS_RX:
                right_x = event.value
                logging.debug(f"Right X-axis value: {right_x}")
            control_tracks(left_y, right_x)

        elif event.type == evdev.ecodes.EV_KEY:
            logging.debug(f"You pressed code {event.code}")
            if event.code == STREAM_TO_HTTP and event.value == 1:   #A
                stop_motors()
                logging.debug("Stream to http button")
                stop_service("rpicam-auto.service")
                start_service("rpicam-vid.service")
                running_search = False
            elif event.code == STREAM_TO_FILE and event.value == 1:   #B
                stop_motors()
                logging.debug("Stream to file button")
                stop_service("rpicam-auto.service")
                start_service("rpicam-file.service")
                running_search = False
            elif event.code == SEARCH_FOR_KNOTWEED and event.value == 1:  #X
                stop_motors()  # Ensure motors are stopped before starting search
                start_service("rpicam-vid.service")
                stop_service("rpicam-file.service")
                start_service("rpicam-auto.service")
                
                running_search = True
                search_thread = threading.Thread(target=run_knotweed_search, daemon=True)
                search_thread.start()

                
    except Exception as e:
        logging.debug(f"Error handling event: {e}")

def stop_service(service_name):
    subprocess.run(["sudo", "systemctl", "stop", service_name], check=True)

def start_service(service_name):
    subprocess.run(["sudo", "systemctl", "start", service_name], check=True)

def restart_service(service_name):
    subprocess.run(["sudo", "systemctl", "restart", service_name], check=True)
    
def detect_knotweed():
    global JSON_FILE_PATH
    """Reads the latest JSON entry and checks for knotweed detection."""
    if not os.path.exists(JSON_FILE_PATH):
        return False  # No file means no detections yet
    
    with open(JSON_FILE_PATH, "r") as file:
        try:
            data = json.load(file)
        except json.JSONDecodeError:
            return False  # Handle incomplete JSON due to writing delays

    # Directly iterate over the array
    for detection in data:
        if detection.get("class_name") == "knotweed-stems" and detection.get("confidence", 0) >= CONFIDENCE_THRESHOLD:
            return True
    
    return False


def run_knotweed_search():
    """Slowly rotates the tank until a knotweed stem is detected or interrupted."""
    global running_search
    print("Starting knotweed search...")
    stop_search_event.clear()  # Ensure the event is not set at the start

    rotate_tank()  # Start rotation

    while not stop_search_event.is_set():  # Check if we should stop
        if detect_knotweed():
            print("Knotweed detected! Stopping rotation.")
            stop_tank()
            running_search = False  # Reset running flag
            return  # Exit gracefully

        time.sleep(0.5)  # Wait before checking again to reduce CPU usage

    print("Search interrupted. Stopping rotation.")
    stop_tank()
    running_search = False  # Reset running flag


# Example motor control functions
def rotate_tank():
    """Placeholder function to rotate the tank."""
    speed = .5
    motor_a.forward(abs(speed))
    motor_b.backward(abs(speed))
    print(f"Rotating tank at speed {speed}...")

def stop_tank():
    """Placeholder function to stop the tank."""
    stop_motors()
    print("Tank stopped.")
    

def main():
    try:
        device = evdev.InputDevice(device_path)
        logging.debug("Listening for joystick input...")
        logging.debug(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Listening for joystick input...")

        for event in device.read_loop():
            handle_event(event)
    except Exception as e:
        logging.debug(f"Error in main loop: {e}")

if __name__ == "__main__":
    main()

