import cv2
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)

# Initialize variables
tracked_objects = {}
next_object_id = 0

# Parameters
confidence_threshold = 0.05
max_distance = 100

def calculate_centroid(bbox):
    """Calculate the centroid of a bounding box."""
    x1, y1, x2, y2 = bbox
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    return cx, cy

def update_tracked_objects(detections):
    """Update tracked objects based on new detections."""
    global tracked_objects, next_object_id

    updated_tracked_objects = {}

    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        cx, cy = calculate_centroid(det["bbox"])

        matched = False
        for obj_id, obj_data in tracked_objects.items():
            prev_cx, prev_cy = calculate_centroid(obj_data["bbox"])
            distance = np.sqrt((cx - prev_cx) ** 2 + (cy - prev_cy) ** 2)

            if distance < max_distance:
                updated_tracked_objects[obj_id] = {
                    "bbox": det["bbox"],
                    "class_name": det["class_name"],
                    "confidence": det["confidence"]
                }
                matched = True
                logging.info(f"Object {obj_id} matched with detection at {(cx, cy)}")
                break

        if not matched:
            updated_tracked_objects[next_object_id] = {
                "bbox": det["bbox"],
                "class_name": det["class_name"],
                "confidence": det["confidence"]
            }
            logging.info(f"New object {next_object_id} created for detection at {(cx, cy)}")
            next_object_id += 1

    tracked_objects = updated_tracked_objects

def main():
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Dummy detections for example purposes
        detections = [
            {"bbox": (50, 50, 150, 150), "class_name": "ObjectA", "confidence": 0.8},
            {"bbox": (200, 200, 300, 300), "class_name": "ObjectB", "confidence": 0.7},
        ]

        # Filter detections by confidence threshold
        detections = [det for det in detections if det["confidence"] >= confidence_threshold]

        # Update tracked objects
        update_tracked_objects(detections)

        # Draw bounding boxes
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            class_name = det["class_name"]
            conf = det["confidence"]

            is_tracked = False
            for obj_id, obj_data in tracked_objects.items():
                if det["bbox"] == obj_data["bbox"]:
                    is_tracked = True
                    # Draw blue bounding box for tracked objects
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                    label = f"Tracked: {class_name} ({conf:.2f})"
                    cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
                    break

            # Draw green bounding box for new detections
            #if not is_tracked:
            #    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            #    label = f"New: {class_name} ({conf:.2f})"
            #    cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # Display the frame
        cv2.imshow("Frame", frame)

        # Break on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

