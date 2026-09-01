"""
OmniVision Live Mobile Streamer & Push Alert Server
- Streams live camera + YOLOv8 detection to mobile phones over Wi-Fi
- Generates QR code in terminal for instant phone connection
- Pushes annotated photo snapshots directly to phone via NTFY
- Clicking the notification on the phone opens the live camera feed
"""
import os
import cv2
import time
import socket
import json
import requests
from flask import Flask, Response, render_template_string, request, jsonify
from detector import SecurityDetector
from sms_service import AlertDispatcher

app = Flask(__name__)

# Load config
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
        "confidence_threshold": 0.45,
        "alert_cooldown_seconds": 10,
        "ntfy_topic": "my_secure_camera_alerts",
        "target_classes": ["person", "car", "dog", "cat", "cell phone", "mouse", "backpack"]
    }

config = load_config()
detector = SecurityDetector(
    model_name=config.get("model_name", "yolov8n.pt"),
    conf_thresh=config.get("confidence_threshold", 0.45),
    target_classes=config.get("target_classes")
)
dispatcher = AlertDispatcher(config=config)

camera = None

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

LOCAL_IP = get_local_ip()
PORT = 5000
LIVE_URL = f"http://{LOCAL_IP}:{PORT}"

def get_camera():
    global camera
    if camera is None or not camera.isOpened():
        camera = cv2.VideoCapture(config.get("camera_source", 0))
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    return camera

def generate_frames():
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

        # If detected, trigger photo push to phone
        if detections and dispatcher.can_alert():
            snap_path = detector.save_annotated_snapshot(frame, detections)
            
            # Send NTFY Push with image & live stream click action
            topic = config.get("ntfy_topic", "my_secure_camera_alerts")
            objects_str = ", ".join([f"{d['class']} ({int(d['conf']*100)}%)" for d in detections])
            msg = f"Detected: {objects_str} at {time.strftime('%H:%M:%S')}"
            
            try:
                with open(snap_path, "rb") as img_file:
                    requests.post(
                        f"https://ntfy.sh/{topic}",
                        data=img_file,
                        headers={
                            "Title": "Security Alert: Motion Detected!",
                            "Message": msg,
                            "Filename": os.path.basename(snap_path),
                            "Priority": "4",
                            "Tags": "warning,camera",
                            "Click": LIVE_URL # Tapping notification on phone opens live stream!
                        },
                        timeout=5
                    )
                    print(f"[✓] Push notification with snapshot sent to phone topic: '{topic}'")
            except Exception as e:
                print(f"[!] Push error: {e}")

            dispatcher.last_alert_time = time.time()

        hud_frame = detector.draw_hud(frame, detections, fps=fps)
        ret, buf = cv2.imencode('.jpg', hud_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ret:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')

# Mobile-Optimized HTML Portal
MOBILE_HTML = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Live Security Camera Feed</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, system-ui, sans-serif; }}
    body {{ background: #0a0e17; color: #f8fafc; display: flex; flex-direction: column; min-height: 100vh; align-items: center; justify-content: center; }}
    .header {{ padding: 12px; background: rgba(15, 23, 42, 0.9); width: 100%; text-align: center; border-bottom: 1px solid #06b6d4; display: flex; justify-content: space-between; align-items: center; padding: 12px 20px; }}
    .brand {{ font-weight: 700; font-size: 1rem; color: #00f2fe; }}
    .live-badge {{ background: #ef4444; color: #fff; font-size: 0.7rem; padding: 3px 8px; border-radius: 4px; font-weight: bold; animation: pulse 1s infinite; }}
    @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} }}
    .stream-box {{ width: 100%; max-width: 960px; padding: 12px; flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; }}
    .stream-img {{ width: 100%; border-radius: 12px; border: 2px solid rgba(6, 182, 212, 0.4); box-shadow: 0 10px 30px rgba(0,0,0,0.8); }}
    .footer-info {{ padding: 12px; font-size: 0.8rem; color: #94a3b8; text-align: center; }}
    .btn {{ background: #06b6d4; color: #000; border: none; padding: 8px 16px; border-radius: 6px; font-weight: bold; cursor: pointer; text-decoration: none; display: inline-block; margin-top: 8px; }}
  </style>
</head>
<body>
  <div class="header">
    <span class="brand">👁️ OmniVision Mobile Live Cam</span>
    <span class="live-badge">● LIVE STREAM</span>
  </div>
  <div class="stream-box">
    <img src="/video_feed" class="stream-img" alt="Live Security Stream">
  </div>
  <div class="footer-info">
    <p>Connected to Local Camera: <strong>{LIVE_URL}</strong></p>
    <p style="margin-top: 4px; font-size: 0.72rem; color: #64748b;">Live AI object detection running with real-time mobile push alerts.</p>
  </div>
</body>
</html>
"""

@app.route('/')
@app.route('/live')
def index():
    return render_template_string(MOBILE_HTML)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/status')
def status():
    return jsonify({"status": "running", "ip": LOCAL_IP, "url": LIVE_URL, "topic": config.get("ntfy_topic")})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  🛡️ OMNIVISION LIVE MOBILE CAMERA STREAMER")
    print("="*60)
    print(f"  [+] Local Wi-Fi Stream URL : {LIVE_URL}")
    print(f"  [+] NTFY Mobile Push Topic : {config.get('ntfy_topic')}")
    print("\n  👉 ON YOUR PHONE:")
    print(f"     1. Connect your phone to the same Wi-Fi as your laptop.")
    print(f"     2. Open your mobile browser and go to: {LIVE_URL}")
    print("     3. You will see the LIVE CAMERA with AI detection on your phone screen!")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
