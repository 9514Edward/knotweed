from ultralytics import YOLO

# dataset is at \mnt\training\datasets\valid\images
# 8n is nano training, 8s is small training

# Load the model.
model = YOLO('yolov8s.pt')
 
# Training.
results = model.train(
   data=r'/home/ubuntu/winterknotweed/datasets/winter-knotweed/images/data.yaml',
   imgsz=640,
   epochs=50,
   batch=8,
   name='yolov8s_v8_50e'
)
