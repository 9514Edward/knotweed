from flask import Flask, Response
import socket

app = Flask(__name__)

@app.route("/")
def index():
    # HTML page to display the stream
    return """
    <html>
        <head>
            <title>Robot</title>
        </head>
        <body>
            <h1>Robot Stream</h1>
            <img src="/stream.mjpeg" alt="Camera Stream" style="display:block; margin-bottom:20px;">
		<audio id="background-music" controls loop style="display:block; margin-top:20px;">
		    <source src="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3" type="audio/mpeg">
		    Your browser does not support the audio element.
		</audio>
		<script>
		    // Autoplay after user interaction
		    document.body.addEventListener('click', () => {
			const audio = document.getElementById('background-music');
			if (audio.paused) {
			    audio.play();
			}
		    });
		</script>
        </body>
    </html>
    """

@app.route("/stream.mjpeg")
def stream():
    def generate():
        HOST = "127.0.0.1"  # Update with your stream's IP
        PORT = 8080            # Update with your stream's port

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((HOST, PORT))
            buffer = b""
            while True:
                # Read raw data from the stream
                data = client_socket.recv(4096)
                if not data:
                    break
                buffer += data

                # Process frames (look for JPEG start and end markers)
                while b"\xff\xd8" in buffer and b"\xff\xd9" in buffer:
                    start = buffer.index(b"\xff\xd8")  # Start of JPEG
                    end = buffer.index(b"\xff\xd9") + 2  # End of JPEG
                    frame = buffer[start:end]
                    buffer = buffer[end:]

                    # Yield MJPEG frame
                    yield (b"--frame\r\n"
                           b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

