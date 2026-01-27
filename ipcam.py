from flask import Flask, Response
import cv2
import numpy as np
import threading
import time

app = Flask(__name__)


class CameraManager:
    def __init__(self):
        self.camera = None
        self.lock = threading.Lock()
        self.last_frame_time = time.time()
        self.frame_timeout = 5
        self.initialize_camera()

    def initialize_camera(self):
        with self.lock:
            if self.camera is not None:
                self.camera.release()

            self.camera = cv2.VideoCapture(1, cv2.CAP_DSHOW)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            for _ in range(5):
                self.camera.read()

    def is_frame_valid(self, frame):
        if frame is None or frame.size == 0:
            return False

        mean_value = np.mean(frame)
        if mean_value < 5:
            return False

        std_value = np.std(frame)
        if std_value < 10:
            return False

        return True

    def read_frame(self):
        with self.lock:
            if self.camera is None or not self.camera.isOpened():
                print("Camera nao aberta, reinicializando...")
                self.initialize_camera()

            success, frame = self.camera.read()

            if not success or not self.is_frame_valid(frame):
                print("Frame invalido detectado, reinicializando camera...")
                self.initialize_camera()

                success, frame = self.camera.read()

                if not success or not self.is_frame_valid(frame):
                    return False, self.create_error_frame()

            self.last_frame_time = time.time()
            return True, frame

    def create_error_frame(self):
        error_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        error_frame[:] = (40, 40, 40)

        text = "Reconectando camera..."
        font = cv2.FONT_HERSHEY_SIMPLEX
        text_size = cv2.getTextSize(text, font, 1, 2)[0]
        text_x = (1280 - text_size[0]) // 2
        text_y = (720 + text_size[1]) // 2

        cv2.putText(error_frame, text, (text_x, text_y), font, 1, (255, 255, 255), 2)

        return error_frame

    def release(self):
        with self.lock:
            if self.camera is not None:
                self.camera.release()


camera_manager = CameraManager()


def gerar_frames():
    consecutive_errors = 0
    max_consecutive_errors = 10

    while True:
        try:
            success, frame = camera_manager.read_frame()

            if not success:
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    print(
                        f"{max_consecutive_errors} erros consecutivos, aguardando 2s..."
                    )
                    time.sleep(2)
                    consecutive_errors = 0
                    camera_manager.initialize_camera()
            else:
                consecutive_errors = 0

            ret, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

            if not ret:
                print("Erro ao codificar frame")
                continue

            frame_bytes = buffer.tobytes()

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )

            time.sleep(0.033)

        except Exception as e:
            print(f"Erro no streaming: {e}")
            time.sleep(1)
            camera_manager.initialize_camera()


@app.route("/video_feed")
def video_feed():
    return Response(
        gerar_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/")
def index():
    return """
    <html>
        <head>
            <title>Camera Stream</title>
            <style>
                body { 
                    background: #1a1a1a; 
                    color: white; 
                    font-family: Arial; 
                    text-align: center;
                    padding: 20px;
                }
                img { 
                    max-width: 90%; 
                    border: 2px solid #333;
                    border-radius: 8px;
                }
            </style>
        </head>
        <body>
            <h1>MPS LIVE TOP</h1>
            <img src="/video_feed" alt="Camera Feed">
        </body>
    </html>
    """


@app.route("/status")
def status():
    is_opened = camera_manager.camera is not None and camera_manager.camera.isOpened()
    return {
        "camera_aberta": is_opened,
        "ultimo_frame": time.time() - camera_manager.last_frame_time,
    }


if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5050, threaded=True)
    finally:
        camera_manager.release()
        cv2.destroyAllWindows()
