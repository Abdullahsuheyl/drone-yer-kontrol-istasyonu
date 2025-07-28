from flask import Flask, render_template, jsonify
from pymavlink import mavutil
import threading
import time
import cv2
from flask import Response
import math

app = Flask(__name__)

# Telemetri veri yapısı
telemetry_data = {
    'pitch': None,
    'roll': None,
    'yaw': None,
    'lat': None,
    'lon': None,
    'alt': None,
    'speed': None,
    'battery': None,
    'voltage': None,
    'mode': None,
    'flight_time': 0
}

# Pixhawk bağlantısı için thread
def pixhawk_thread():
    connection = mavutil.mavlink_connection('COM12', baud=57600)
    connection.wait_heartbeat()
    
    # Veri akışlarını etkinleştir
    connection.mav.request_data_stream_send(
        connection.target_system,
        connection.target_component,
        mavutil.mavlink.MAV_DATA_STREAM_ALL,
        4,  # 4 Hz
        1    # Enable
    )
    
    start_time = time.time()
    
    while True:
        msg = connection.recv_msg()
        if msg:
            process_mavlink_message(msg)
        telemetry_data['flight_time'] = int(time.time() - start_time)
        time.sleep(0.01)

def process_mavlink_message(msg):
    msg_type = msg.get_type()
    
    if msg_type == "ATTITUDE":
        telemetry_data['pitch'] = math.degrees(msg.pitch)
        telemetry_data['roll'] = math.degrees(msg.roll)
        telemetry_data['yaw'] = math.degrees(msg.yaw)
    
    elif msg_type == "GLOBAL_POSITION_INT":
        telemetry_data['lat'] = msg.lat / 1e7
        telemetry_data['lon'] = msg.lon / 1e7
        telemetry_data['alt'] = msg.relative_alt / 1000  # metre cinsinden
        telemetry_data['speed'] = math.sqrt(msg.vx**2 + msg.vy**2 + msg.vz**2) / 100  # m/s
    
    elif msg_type == "SYS_STATUS":
        telemetry_data['battery'] = msg.battery_remaining
        telemetry_data['voltage'] = msg.voltage_battery / 1000  # volt cinsinden
    
    elif msg_type == "HEARTBEAT":
        telemetry_data['mode'] = mavutil.mode_string_v10(msg)

# Kamera akışı için thread
def generate_frames():
    camera = cv2.VideoCapture(0)  # Jetson kamera
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_orientation')
def get_orientation():
    return jsonify(telemetry_data)


# ARM endpoint
@app.route('/arm', methods=['POST'])
def arm_drone():
    try:
        connection = mavutil.mavlink_connection('COM12', baud=57600)
        connection.wait_heartbeat()

        # Mod değiştirme yok! Kumandadaki mod kullanılacak (örneğin Stabilize)

        # ARM komutu gönder
        connection.mav.command_long_send(
            connection.target_system,
            connection.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            1, 0, 0, 0, 0, 0, 0
        )
        print("ARM komutu gönderildi (manuel uçuş).")
        return "Drone ARM edildi (manuel kontrol)", 200
    except Exception as e:
        return f"Hata: {e}", 500



if __name__ == '__main__':
    # Pixhawk thread'ini başlat
    threading.Thread(target=pixhawk_thread, daemon=True).start()
    
    # Flask uygulamasını çalıştır
    app.run(host='0.0.0.0', port=5000, threaded=True)