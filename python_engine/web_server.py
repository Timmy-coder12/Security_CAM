"""
OmniVision Security Camera - Web Management & Remote Telemetry Server
"""
import os
import cv2
import time
import json
from flask import Flask, render_template, Response, jsonify, request, send_from_directory
from detector import SecurityDetector
from sms_service import AlertDispatcher

app = Flask(__name__, template_folder='../web_dashboard', static_folder='../web_dashboard')

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "camera_source": 0,
        "model_name": "yolov8n.pt",
        "confidence_threshold": 0.50,
        "alert_cooldown_seconds": 30,
        "target_phone_number": "+1234567890",
        "ntfy_enabled": True,
        "ntfy_topic": "my_security_cam_alert_feed",
        "twilio_enabled": False,
        "twilio_account_sid": "",
        "twilio_auth_token": "",
        "twilio_from_number": "",
        "target_classes": ["person", "car", "dog", "cell phone"],
        "security_zone": None
    }

config = load_config()
detector = SecurityDetector(
    model_name=config.get("model_name", "yolov8n.pt"),
    conf_thresh=config.get("confidence_threshold", 0.5),
    target_classes=config.get("target_classes", [])
)
dispatcher = AlertDispatcher(config=config)
camera = None

def get_camera():
    global camera
    if camera is None or not camera.isOpened():
        camera = cv2.VideoCapture(config.get("camera_source", 0))
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    return camera

def generate_stream():
    cam = get_camera()
    prev_time = time.time()
    while True:
        success, frame = cam.read()
        if not success:
            time.sleep(0.05)
            continue

        detections = detector.detect(frame)
        now = time.time()
        fps = int(1.0 / (now - prev_time + 1e-6))
        prev_time = now

        # Security alert trigger logic
        zone = config.get("security_zone")
        should_alert = False
        if detections:
            if zone:
                for d in detections:
                    if detector.check_intrusion(d, zone):
                        should_alert = True
                        break
            else:
                should_alert = True

        if should_alert and dispatcher.can_alert():
            snap_path = detector.save_annotated_snapshot(frame, detections)
            dispatcher.send_alert_async(detections, snap_path, "Security Zone" if zone else "Camera FOV")

        hud_frame = detector.draw_hud(frame, detections, fps=fps, zone=zone)
        ret, buf = cv2.imencode('.jpg', hud_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ret:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    global config
    if request.method == 'POST':
        data = request.get_json() or {}
        config.update(data)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        detector.conf_thresh = config.get("confidence_threshold", 0.5)
        detector.target_classes = set(config.get("target_classes", []))
        dispatcher.config = config
        dispatcher.cooldown_sec = config.get("alert_cooldown_seconds", 30)
        return jsonify({"success": True, "config": config})
    return jsonify(config)

@app.route('/api/test_sms', methods=['POST'])
def test_sms():
    data = request.get_json() or {}
    phone = data.get("phone", config.get("target_phone_number"))
    msg = f"🧪 TEST ALERT: OmniVision Security System is connected to {phone}!"
    
    # Trigger dispatch
    test_obj = [{"class": "System Test", "conf": 0.99, "bbox": [0,0,100,100]}]
    dispatcher.send_alert_async(test_obj)
    return jsonify({"success": True, "message": f"Test alert dispatched to {phone} and NTFY topic."})

@app.route('/api/alerts/<path:filename>')
def get_alert_image(filename):
    return send_from_directory('alerts', filename)

if __name__ == '__main__':
    print("\n==========================================")
    print("  OmniVision Security Cam Web Portal")
    print("  Open http://127.0.0.1:5000 in your browser")
    print("==========================================\n")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
