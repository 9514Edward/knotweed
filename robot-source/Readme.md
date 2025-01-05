# Startup files
## Currently enabled service files are: 
  - joystick.service > this service listens to the bluetooth game controller and allows manual driving.
  - rpicam-vid.service > this service streams the camera to tcp://127.0.0.1:8080, waiting to be picked up.  If nobody picks it up, it crashes and restarts until it is picked up.
  - rpicam-file.service > this service is started when the joystick controller B button is pressed.  It streams the video stream to mp4 files of 5 minutes duration on the RasPI instead of TCP.  Pressing the A button reverts to tcp streaming.
  - webserver.service > this service starts the webserver app /home/efelsenthal/Projects/webserver/app.py.  This app serves a web page that plays robotic music and the tcp stream from rpicam-vid.service. On the RasPI: http://localhost:5000.  Can also be streamed to a networked computer by pointing the browser to the IP of the ras pi, ie http://192.168.1.68:5000.  Only one browser can watch at a time.  
  -![stream](https://github.com/user-attachments/assets/47d52f83-f353-487d-9944-b4990953498c)
