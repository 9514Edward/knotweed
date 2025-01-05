# Startup files
## Currently enabled service files are: 
    - joystick.service > this service listens to the bluetooth game controller and allows manual driving
    - rpicam-vid.service > this service streams the camera to tcp://127.0.0.1:8080, waiting to be picked up.  If nobody picks it up, it crashes and restarts until it is picked up.
    - webserver.serice > this service starts the webserver app /home/efelsenthal/Projects/webserver/app.py.  This app serves a web page that plays robotic music and the tcp stream from rpicam-vid.service.
