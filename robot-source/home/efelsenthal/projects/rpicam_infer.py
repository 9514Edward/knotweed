import cv2
import logging
from ultralytics import YOLO
import os
import time
import json

# Logging setup
logging.basicConfig(filename='/home/efelsenthal/rpicam_infer.log', level=logging.DEBUG)

# YOLO Model Path
model_path = "/home/efelsenthal/Projects/models/best.pt"
model = YOLO(model_path)
logging.info(f"Model loaded from {model_path}")

# Confidence threshold for inference
confidence_threshold = 0.07



def infer(frame, output_infer_dir, json_output_file):
    """Run inference on the frame, save the annotated frame, and log results in JSON."""
    # Perform inference using the model
    results = model.predict(frame, conf=confidence_threshold)
    
    # Log results to verify detections
    if not results:
        logging.warning("No results returned from the model.")
    
    timestamp = time.strftime('%H-%M-%S', time.gmtime(time.time()))
    annotated_filename = os.path.join(output_infer_dir, f"annotated_{timestamp}.jpg")
    frame_data = {"timestamp": timestamp, "image_file": annotated_filename, "detections": []}

    # Annotate the frame with results
    for result in results:
        if hasattr(result, 'boxes') and result.boxes is not None:
            for box in result.boxes.data:
                x1, y1, x2, y2, conf, cls = box[:6]
                logging.debug(f"Detected box: {x1}, {y1}, {x2}, {y2}, Confidence: {conf}")

                if conf >= confidence_threshold:
                    class_name = model.names[int(cls)]
                    
                    # Draw bounding boxes and labels
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    label = f"{class_name} ({conf:.2f})"
                    cv2.putText(frame, label, (int(x1), int(y1) - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                    # Append detection details to frame data
                    frame_data["detections"].append({
                        "class_name": class_name,
                        "confidence": float(conf),
                        "bbox": [int(x1), int(y1), int(x2), int(y2)]
                    })

    # Save annotated frame
    cv2.imwrite(annotated_filename, frame)
    logging.info(f"Saved annotated frame: {annotated_filename}")

    # Append frame data to JSON file
    try:
        with open(json_output_file, "r+") as f:
            data = json.load(f)
            data.append(frame_data)
            f.seek(0)
            json.dump(data, f, indent=4)
        logging.info(f"Frame data appended to JSON: {frame_data}")
    except Exception as e:
        logging.error(f"Error while writing to JSON file: {str(e)}")


def capture_frames(url, interval):
    """Capture frames from the video stream at a set interval."""
    logging.info("Starting camera inference script...")
    cap = cv2.VideoCapture(url)

    if not cap.isOpened():
        logging.error("Failed to open the TCP stream.")
        return

    logging.info("Successfully connected to the stream.")

    # Setup directories
    output_dir = "/home/efelsenthal/frame_debug"
    annotated_dir = "/home/efelsenthal/frame_annotated"

    # Ensure directories exist
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(annotated_dir, exist_ok=True)
    
    # Clear existing files in directories
    for folder in [output_dir, annotated_dir]:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
    
    # JSON output file
    json_output_file = "/home/efelsenthal/frame_annotated/annotations.json"

    # Check if the JSON file exists, if not, create it
    if not os.path.exists(json_output_file):
        try:
            with open(json_output_file, "w") as f:
                json.dump([], f)
            logging.info(f"Created new JSON file at {json_output_file}")
        except Exception as e:
            logging.error(f"Failed to create JSON file: {str(e)}")
            raise



    start_time = time.time()
    frame_count = 0

    while True:
        cap.grab()  # Attempt to grab a frame

        if time.time() - start_time >= interval:
            ret, frame = cap.read()  # Decode the grabbed frame
            if not ret:
                logging.warning("Frame capture returned False. No frame received.")
                continue

            # Save the raw frame
            timestamp = time.strftime('%H-%M-%S', time.gmtime(time.time()))
            frame_filename = os.path.join(output_dir, f"frame_{timestamp}.jpg")
            cv2.imwrite(frame_filename, frame)
            logging.info(f"Saved raw frame: {frame_filename}")

            # Perform inference and save annotated frame
            infer(frame, annotated_dir, json_output_file)

            start_time = time.time()
            frame_count += 1

        # Stop after a certain number of frames (optional)
        if frame_count > 100:
            logging.info("Captured 100 frames. Exiting.")
            break

    cap.release()
    logging.info("Camera inference script completed.")

if __name__ == "__main__":
    stream_url = "tcp://127.0.0.1:8080"
    capture_interval = 1.5
    capture_frames(stream_url, capture_interval)

