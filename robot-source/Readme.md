# Startup files
## Currently service files are: 
  ## running on boot (enabled)
  - joystick.service > this service listens to the bluetooth game controller and allows manual driving as well as toggling between TCP streaming or to MP4 files nstead of TCP.
  ## started and stopped via joystick service
  - rpicam-file.service > this service is started when the joystick controller B button is pressed.  It streams the video stream to mp4 files of 2.5 minutes (150000 milliseconds) duration on the RasPI
  - rpicam-vid.service > this service streams the camera to tcp://127.0.0.1:8080, waiting to be picked up.  If nobody picks it up, it crashes and restarts until it is picked up.   Pressing the A button reverts to tcp streaming.  The viewer will need to refresh the page to pick up the stream again.
  - rpicam-auto.service > works in conjunction with rpicam-vid.service and launches rpicam_infer.py to self drive the robot.  Requires rpicam-vid.service.
  ## other
  - webserver.service 
  - this service starts the webserver app /home/efelsenthal/Projects/webserver/app.py.  This app serves a web page that plays robotic music and the tcp stream from rpicam-vid.service. On the RasPI: http://localhost:5000.  Can also be streamed to a networked computer by pointing the browser to the IP of the ras pi, ie http://192.168.1.68:5000.  Only one browser can watch at a time.  
  ![stream](https://github.com/user-attachments/assets/47d52f83-f353-487d-9944-b4990953498c)
## rpicam-auto.service
  - this service starts rpicam_infer.py which captures a frame from the TCP stream every 20th frame (every 1.5 seconds - the stream is 15 fps) and it runs inference and saves the annotated jpg files for reference and possible re-training and the inference results to a json file.
  - Examples below:
  - ![annotated_00-59-16](https://github.com/user-attachments/assets/bf7f0e74-a455-434b-be5d-9d592d35b804)

  ```json
   {
        "timestamp": "02-39-42",
        "image_file": "/home/efelsenthal/frame_annotated/annotated_02-39-42.jpg",
        "detections": [
            {
                "class_name": "knotweed-stems",
                "confidence": 0.13095226883888245,
                "bbox": [
                    119,
                    35,
                    276,
                    478
                ]
            }
        ]
    },
```
