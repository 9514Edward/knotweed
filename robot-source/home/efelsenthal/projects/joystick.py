import evdev
from gpiozero import Motor
import logging
from datetime import datetime
import os
import subprocess

logging.basicConfig(filename='/home/efelsenthal/joystick.log', level=logging.DEBUG)
logging.debug('Motor control service started')

# GPIO pin setup for Motor Driver 1 (Motors A and B)
IN1_A = 17
IN2_A = 27
IN3_A = 22
IN4_A = 23

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

STREAM_TO_HTTP = 305
STREAM_TO_FILE = 304

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
    try:
        motor_a.stop()
        motor_b.stop()
        logging.debug("All motors stopped.")
    except Exception as e:
        logging.debug(f"Error stopping motors: {e}")

def handle_event(event):
    global left_y, right_x
    try:
        if event.type == evdev.ecodes.EV_ABS:
            if event.code == evdev.ecodes.ABS_Y:
                left_y = event.value
                logging.debug(f"Left Y-axis value: {left_y}")
            elif event.code == evdev.ecodes.ABS_RX:
                right_x = event.value
                logging.debug(f"Right X-axis value: {right_x}")
            control_tracks(left_y, right_x)

        elif event.type == evdev.ecodes.EV_KEY:
            if event.code == STREAM_TO_HTTP and event.value == 1:
                stop_service("rpicam-file.service")
                start_service("rpicam-vid.service")
            elif event.code == STREAM_TO_FILE and event.value == 1:
                stop_service("rpicam-vid.service")
                start_service("rpicam-file.service")
    except Exception as e:
        logging.debug(f"Error handling event: {e}")

def stop_service(service_name):
    subprocess.run(["sudo", "systemctl", "stop", service_name], check=True)

def start_service(service_name):
    subprocess.run(["sudo", "systemctl", "start", service_name], check=True)

def restart_service(service_name):
    subprocess.run(["sudo", "systemctl", "restart", service_name], check=True)

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

