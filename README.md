# Knotweed Terminator Robot
## Also, see the other README  
You can find additional details in the [README Robot Code at GitHub](https://github.com/9514Edward/winterknotweed/tree/main/robot-source#startup-files).  

## Introduction
  - The goal of this project is a tank tread robot which can with occasional human assist navigate throughout a patch of knotweed and terminate it -- aka remediatition.  I envision a single operator with about 6 robots deployed at once to remediate a 1,000 square foot patch in about an hour.  Also other models for other plants such as English Ivy.
  - The dataset was annotated on RoboFlow with a monthly subscription ($65), leveraging their Label Assist tool to rapidly draw bounding boxes, then I reviewed all images manually and made corrections/deletions/additions as needed to all the annotations.  Then I downloaded the dataset as shown in the datasets folder here.
  - I have used my AWS account to train on an AWS GPU for a minimal hourly cost because training takes less than an hour.
  - The next generation (prototype) robot will need to map the target area, probably with lidar and require more advanced autonomous steering features as well as remediation attachments.
  - In August I will photograph living knotweed and retrain. August/September is the optimal time to terminate knotweed.
  - I have until then to develop the robot.

## Next Steps
 - Next step is to collect more photos though the video I will take through the robot in the field.  Then retrain and learn better the tools for model training. Before doing this I need to document and memorize steps to 1) create hotspot on phone 2) power up robot 3) connect to bluetooth controller 4) make sure I know which button streams to the phone and which streams to disk.
 - After that, will get basic driving action of scanning 360 degrees, find knotweed, approach it and stop when the bounding box reaches a certain percentage of the screen.

## Status at Jan 26, 2025
  - Giving up on object tracking as not able to get it working and not a priority

## Status at Jan 12, 2025
  - Collaborators are welcome.  Email me at titlesync@gmail.com
  - Today reached milestone of running inference in real time on the robot, identified a knotweed stem (albeit incorrectly due to needing more training and having a very low confidence parameter), and wrote the the bounding box coordinates to a file in anticipation of the next step which will be to direct the steering towards the knotweed and stop when it is reached.  See the illustrations [ here: rpicam-auto.service!](https://github.com/9514Edward/winterknotweed/tree/main/robot-source#rpicam-autoservice)
    
## Status at Jan 5, 2025
  - Collaborators are welcome.  Email me at titlesync@gmail.com  I am already collaborating with chat GPT 3 and Google.  I have no education or training on the software and hardware discussed in this project but I am capable of asking the right questions of the right tools to get things to work.
  - A small testbed tank tread robot is assembled with tread controller and camera.  It is integrated with an off the shelf bluetooth game controller and can drive around via manual inputs from the game controller.
  - PyTorch Ultralytics small computer vision model has been created from 120 images and is based on the COCO framework and works only with confidence level of 12% or so.  Many more training photos are needed.
    
## Training steps
  - Purchase an AWS EC2 P3 Instance
     - Deep Learning OSS Nvidia Driver AMI GPU TensorFlow 2.18 (Ubuntu 22.04)
     - g4dn 12XLarge $6.12 and hour
     - created a pem key for access (computervision.pem)
     - Allowing ssh access from my IP
  - Logged in via ssh
  - ssh -i C:\Users\User\source\python\winter_knotweed\computervision.pem ubuntu@ec2-52-206-140-136.compute-1.amazonaws.com
  - sudo apt install gh
  - gh auth login
  - Back on your web-browser make a token
    - Github>Settings>Developer Setting>Personal access tokens>Tokens (classic)
    - Scopes:  repo, admin, admin public key
  - gh auth login>GitHub.com>SSH>/home/ubuntu/.ssh/id_ed25519.pub>Paste your authentication token>
  - gh repo clone 9514Edward/winterknotweed
  - cd winterknotweed/source/training
  - pip install ultralytics (takes about 5 minutes)
  - python3 train.py (training only takes 3 minutes for small or medium)
  - git add .
  - git commit -m "Add YOLOv8 small training results and model weights"
  - git push origin main
  - Now I have the pytorch model file source/training/runs/detect/yolov8s_v8_50e2/weights/best.pt (the best small model after training) which I can use for inference testing and in my robot code.
  - Terminate the instance.  Total time with the EC2 instance took just over an hour due to learning curve and documentation here.
  - The Dave 209 robot test bed
  - ![20250104_192800 (Small)](https://github.com/user-attachments/assets/59fe39b7-ece7-4dbe-a2ac-2eb8297dff12)
 
## Debugging
  - If unable to connect to bluetooth after booting multiple times.  Need to run sudo rfkill unblock bluetooth


