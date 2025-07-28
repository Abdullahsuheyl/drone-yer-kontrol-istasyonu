from flask import Flask, Response, send_from_directory, request
import cv2
from ultralytics import YOLO
import serial
import time
import threading

app = Flask(__name__)
model = YOLO("last.pt")

# Arduino bağlantısı
try:
    arduino = serial.Serial('/dev/ttyUSB0', 9600)
    time.sleep(2)
    print("Arduino bağlantısı kuruldu.")
except Exception as e:
    print(f"Arduino bağlantı hatası: {e}")
    arduino = None

# Kamera bağlantısı
gst_pipeline = (
    "nvarguscamerasrc ! "
    "video/x-raw(memory:NVMM), width=1280, height=720, format=NV12, framerate=30/1 ! "
    "nvvidconv flip-method=0 ! "
    "video/x-raw, width=640, height=480, format=BGRx ! "
    "videoconvert ! "
    "video/x-raw, format=BGR ! appsink"
)
camera = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

# Püskürtme kontrolü (pencere ile bağlantılı)
spray_control = {
    'manual_override': False,
    'manual_state': b'1'
}

lock = threading.Lock()

def generate_frames():
    start_x, end_x = 213, 426
    start_y, end_y = 240, 480

    retry = 0
    while retry < 30:
        success, frame = camera.read()
        if success:
            break
        print("Kamera başlatılıyor...")
        time.sleep(0.1)
        retry += 1
    else:
        print("Kamera açılmadı.")
        return

    while True:
        success, frame = camera.read()
        if not success:
            time.sleep(0.1)
            continue

        results = model(frame)[0]
        pencere_tespit_edildi = False

        for result in results.boxes.data.tolist():
            x1, y1, x2, y2, score, ID = result
            x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

            if score >= 0.7 and (start_x <= cx <= end_x) and (start_y <= cy <= end_y):
                if int(ID) == 0:
                    pencere_tespit_edildi = True
                label = "pencere" if int(ID) == 0 else f"Nesne {int(ID)}"
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.putText(frame, label, (x1, y1 + 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

        cv2.rectangle(frame, (start_x, start_y), (end_x, end_y), (0, 255, 0), 2)

        if arduino:
            try:
                with lock:
                    if pencere_tespit_edildi:
                        arduino.write(b'1')  # pencere varsa püskürtme kapalı
                    elif spray_control['manual_override']:
                        arduino.write(spray_control['manual_state'])  # manuel kontrol
                    else:
                        arduino.write(b'1')  # varsayılan kapalı
            except Exception as e:
                print(f"Arduino yazma hatası: {e}")

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    camera.release()

# Ana Sayfa
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Püskürtme kontrol
@app.route('/spray/on', methods=['POST'])
def spray_on():
    with lock:
        spray_control['manual_override'] = True
        spray_control['manual_state'] = b'0'
    return 'Püskürtme açıldı', 200

@app.route('/spray/off', methods=['POST'])
def spray_off():
    with lock:
        spray_control['manual_override'] = True
        spray_control['manual_state'] = b'1'
    return 'Püskürtme kapatıldı', 200

# KAPAK kontrol tamamen manuel
@app.route('/kapak/on', methods=['POST'])
def kapak_on():
    if arduino:
        try:
            arduino.write(b'2')  # Kapak Aç
            print("Kapak açıldı (komut: b'2')")
        except Exception as e:
            print(f"Kapak açma hatası: {e}")
    return 'Kapak açıldı', 200

@app.route('/kapak/off', methods=['POST'])
def kapak_off():
    if arduino:
        try:
            arduino.write(b'3')  # Kapak Kapat
            print("Kapak kapatıldı (komut: b'3')")
        except Exception as e:
            print(f"Kapak kapatma hatası: {e}")
    return 'Kapak kapatıldı', 200

# Flask sunucusu
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
