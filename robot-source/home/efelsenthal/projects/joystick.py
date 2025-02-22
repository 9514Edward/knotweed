import evdev
from gpiozero import Motor
import logging
from datetime import datetime
import os
import subprocess
import json
import time
import threading
import shutil
import cv2

stop_search_event = threading.Event()


logging.basicConfig(filename='/home/pi/joystick.log', level=logging.DEBUG)
logging.debug('Motor control service started')

# GPIO pin setup for Motor Driver 1 (Motors A and B)
IN1_A = 17
IN2_A = 27
IN3_A = 22
IN4_A = 23

CONFIDENCE_THRESHOLD = 0.08
running_search = False
JSON_FILE_PATH = "/home/pi/frame_annotated/annotations.json"
ANNOTATED_PATH = "/home/pi/frame_annotated"
STREAM_PATH =  "/home/pi/frame_debug"
CONFIDENCE_THRESHOLD = 0
IMAGE_WIDTH = 640


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
        #stop_search_event.set()  # Signal search thread to stop
        logging.debug("All motors stopped. ")
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
                stop_search_event.set()
                logging.debug("Stream to http button")
                stop_service("rpicam-auto.service")
                start_service("rpicam-vid.service")
                if running_search == True:
                    finalize_folders()
                running_search = False
            elif event.code == STREAM_TO_FILE and event.value == 1:   #B
                stop_motors()
                stop_search_event.set()
                logging.debug("Stream to file button")
                stop_service("rpicam-auto.service")
                start_service("rpicam-file.service")
                if running_search == True:
                    finalize_folders()                
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
    logging.debug(f"Looking for file {JSON_FILE_PATH}")
    
    if not os.path.exists(JSON_FILE_PATH):
        return None, None  # No file means no detections yet

    logging.debug("JSON FILE DETECTED!")
    
    try:
        with open(JSON_FILE_PATH, "r") as file:
            logging.debug("Opened the JSON file")
            data = json.load(file)  # Ensure data is a list
            logging.debug(f"Data loaded: {data}")
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON in {JSON_FILE_PATH}")
        return None, None  # Handle incomplete JSON
    except Exception as e:
        logging.error(f"Error reading or processing in detect {JSON_FILE_PATH}: {e}")
        return None, None  # Handle other errors

    if not isinstance(data, list):
        logging.error("JSON data is not a list, check file format!")
        return None, None

    # Iterate over each entry in the list
    for entry in data:
        if not isinstance(entry, dict):
            logging.warning("Skipping non-dictionary entry in JSON list")
            continue  # Skip if entry is not a dictionary
        
        if "detections" in entry:
            logging.debug("IN DETECTIONS")
            filename = entry.get("image_file", "unknown_filename.jpg")  # Default if missing

            for detection in entry["detections"]:
                logging.debug("IN DETECTION")
                class_name = detection.get("class_name")
                confidence = detection.get("confidence", 0)

                logging.debug(f"DETECTION HAPPENED! Class: {class_name}, Confidence: {confidence}")

                if class_name == "knotweed-stems" and confidence >= CONFIDENCE_THRESHOLD:
                    return detection, filename  # Return the first valid detection

    return None, None  # No valid detection found

def navigate_to_knotweed(detection, filename):
    """Continuously adjusts robot movement based on latest detection data for 4 seconds."""
    try:
        global IMAGE_WIDTH, JSON_FILE_PATH
        first_iteration = True

        logging.debug("Navigating to knotweed")

        for _ in range(16):  # Loop for 4 seconds (0.25-second intervals)
            try:
                # Read the latest detection data
                if first_iteration == False:
                    logging.info(f"the file being read {JSON_FILE_PATH}")
                    with open(JSON_FILE_PATH, 'r') as f:
                        data = json.load(f)
                        
                        # Loop through each frame in the data
                        for frame in data:
                            # Find all detections with class_name 'knotweed-stems' in the current frame
                            detections = frame.get("detections", [])
                            knotweed_detections = [d for d in detections if d.get("class_name") == "knotweed-stems"]

                            if knotweed_detections:
                                # Get the highest confidence detection in the current frame
                                detection = max(knotweed_detections, key=lambda d: d.get("confidence", 0))
                                # Get the image_file associated with this frame
                                filename = frame.get("image_file", "default_filename.jpg")  #Since we are navigating, it may be a newer detection than the original one
                                logging.info(f"Selected detection: {detection}")
                                logging.info(f"Image file: {filename}")
                            else:
                                logging.error("No 'knotweed-stems' detections found in this frame.")
                                filename = "default_filename.jpg"
                        
                        
                    logging.info(f"The json loaded was {detection}")
                else:
                    first_iteration = False
                
                if 'bbox' in detection:
                    bbox_center_x = (detection['bbox'][0] + detection['bbox'][2]) / 2  # Center of bounding box
                    screen_center_x = IMAGE_WIDTH / 2  # Center of the screen
                    offset = (bbox_center_x - screen_center_x) / IMAGE_WIDTH

                    # Adjust movement based on offset
                    if offset < 0:  # Object is to the left
                        left_tread_speed = max(0, 1.0 + offset)  # Reduce left tread speed
                        right_tread_speed = 1.0  # Keep right tread at full speed
                    elif offset > 0:  # Object is to the right
                        right_tread_speed = max(0, 1.0 - offset)  # Reduce right tread speed
                        left_tread_speed = 1.0  # Keep left tread at full speed
                    else:
                        left_tread_speed = right_tread_speed = 1.0  # Move straight

                else:
                    logging.warning("No valid detection found. Moving straight.")
                    left_tread_speed = right_tread_speed = 1.0  # Default behavior when no detection

                logging.debug(f"Detection: {detection} Updated speeds - Left: {left_tread_speed:.2f}, Right: {right_tread_speed:.2f}")

                # Find annotated image and update it
                if  os.path.exists(filename):
                    annotate_image_with_speeds(filename, left_tread_speed, right_tread_speed)
                else:
                    logging.warning(f"Annotated image file not found: {filename}")

                # Adjust motor speeds
                motor_a.backward(abs(left_tread_speed))
                motor_b.backward(abs(right_tread_speed))

            except Exception as e:
                logging.error(f"Error reading or processing in navigate to knotweed {JSON_FILE_PATH}: {e}")
                left_tread_speed = right_tread_speed = 1.0  # Continue straight if an error occurs
                motor_a.backward(abs(left_tread_speed))
                motor_b.backward(abs(right_tread_speed))

            time.sleep(0.25)  # Wait .25 second before re-checking

        # Stop movement after 4 seconds
        finalize_folders()
        stop_tank()
        stop_search_event.set()
        stop_service("rpicam-auto.service")
        

    except Exception as e:
        logging.error(f"Error in navigate_to_knotweed: {e}")


def run_knotweed_search():
    """Rotates the tank until a knotweed stem is detected, then drives towards it while keeping it centered."""
    global running_search
    logging.debug("Starting knotweed search...")
    stop_search_event.clear()  # Ensure the event is not set at the start

    rotate_tank()  # Start rotation

    while not stop_search_event.is_set():  # Check if we should stop
        time.sleep(0.2)  #let it rotated for a moment
        stop_tank()
        logging.debug("going to sleep")
        time.sleep(1.5)  #wait a sec to see if it finds something
        detection, filename = detect_knotweed()
        if detection and filename:
            logging.debug("Knotweed detected! Stopping rotation.")
            stop_tank()  # Stop the rotation
            logging.debug(f"Knotweed detected! Navigating to {detection}.")
            navigate_to_knotweed(detection, filename)
            running_search = False  # Reset running flag
            return  # Exit gracefully
        rotate_tank()  #start rotating again if nothing found.
        logging.debug(f"returning to top of while with stop search event set = {stop_search_event.is_set()}")

    logging.debug("Search interrupted.")
    stop_tank()
    running_search = False  # Reset running flag

def annotate_image_with_speeds(filename, left_tread_speed, right_tread_speed):
    """Annotates an image with left and right tread speeds."""
    image = cv2.imread(filename)
    if image is None:
        logging.error(f"Failed to load image: {filename}")
        return

    # Overlay tread speeds in blue
    speed_text = f"Left Tread: {left_tread_speed:.2f} | Right Tread: {right_tread_speed:.2f}"
    cv2.putText(image, speed_text, (10, image.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    # Save the updated annotated image
    cv2.imwrite(filename, image)



def finalize_folders():
    global ANNOTATED_PATH
    global STREAM_PATH
    
    logging.info("Starting Finalization")
    timestamp_dir = time.strftime('%Y-%m-%d_%H-%M-%S', time.gmtime())

    # Get base directories, since ANNOTATED_PATH and STREAM_PATH include "latest"
    base_annotated_path = ANNOTATED_PATH
    base_stream_path = STREAM_PATH
    
    # Create timestamped archive directories
    new_annotated_dir = os.path.join(base_annotated_path, timestamp_dir)
    new_stream_dir = os.path.join(base_stream_path, timestamp_dir)

    os.makedirs(new_annotated_dir, exist_ok=True)
    os.makedirs(new_stream_dir, exist_ok=True)

    # Set full permissions (read, write, execute for user, group, and others)
    os.chmod(new_annotated_dir, 0o777)
    os.chmod(new_stream_dir, 0o777)

    # Move files from the "latest" folder to the timestamped archive
    shutil.copy("/home/pi/joystick.log", new_annotated_dir)
    shutil.copy("/home/pi/rpicam_infer.log", new_annotated_dir)

    for file in os.listdir(ANNOTATED_PATH):
        src = os.path.join(ANNOTATED_PATH, file)
        dst = os.path.join(new_annotated_dir, file)
        if os.path.isfile(src):
            shutil.move(src, dst)

    for file in os.listdir(STREAM_PATH):
        src = os.path.join(STREAM_PATH, file)
        dst = os.path.join(new_stream_dir, file)
        if os.path.isfile(src):
            shutil.move(src, dst)

    logging.info(f"Archived files to {new_annotated_dir} and {new_stream_dir}")



def initialize_folder():
    global ANNOTATED_PATH
    folder_path = f"{ANNOTATED_PATH}"
    # Check if the directory exists
    print(f"Annotated path {folder_path}")
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        # Loop through all files in the folder and delete them
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            print(f"file_path {file_path}")
            try:
                if os.path.isfile(file_path):  # Make sure it's a file
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")
    else:
        print(f"The folder {folder_path} does not exist or is not a directory.")

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

