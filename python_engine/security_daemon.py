"""
24/7 Security Camera Monitor & SMS Alert Daemon
Runs continuously, detects targets via YOLOv8, and sends real SMS / Mobile Push with photos.
"""
import os
import cv2
import time
import json
import argparse
from detector import SecurityDetector
from sms_service import AlertDispatcher

def load_config(config_path="config.json"):
    default_config = {
        "camera_source": 0,
        "model_name": "yolov8n.pt",
        "confidence_threshold": 0.50,
        "alert_cooldown_seconds": 30,
        "target_phone_number": "+1234567890",
        
        "ntfy_enabled": True,
        "ntfy_topic": "my_security_cam_alert_feed",

        "twilio_enabled": False,
        "twilio_account_sid": "AC_YOUR_TWILIO_SID",
        "twilio_auth_token": "YOUR_TWILIO_AUTH_TOKEN",
        "twilio_from_number": "+1XXXXXXXXXX",

        "telegram_enabled": False,
        "telegram_bot_token": "YOUR_BOT_TOKEN",
        "telegram_chat_id": "YOUR_CHAT_ID",

        "target_classes": ["person", "car", "dog", "cat", "cell phone", "backpack", "mouse"],
        "security_zone": None,
        "save_local_snapshots": True,
        "headless_mode": False
    }

    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                user_conf = json.load(f)
                default_config.update(user_conf)
                print(f"[+] Loaded config from {config_path}")
        except Exception as e:
            print(f"[!] Error loading {config_path}: {e}")
    else:
        with open(config_path, "w") as f:
            json.dump(default_config, f, indent=4)
        print(f"[+] Created default configuration template at {config_path}")

    return default_config

def main():
    parser = argparse.ArgumentParser(description="24/7 Security Cam SMS Daemon")
    parser.add_argument("--config", default="config.json", help="Path to config.json")
    parser.add_argument("--source", default=None, help="Override camera source (0 or RTSP URL)")
    parser.add_argument("--headless", action="store_true", help="Run without graphical display")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.source is not None:
        config["camera_source"] = int(args.source) if args.source.isdigit() else args.source
    if args.headless:
        config["headless_mode"] = True

    # Initialize Modules
    detector = SecurityDetector(
        model_name=config.get("model_name", "yolov8n.pt"),
        conf_thresh=config.get("confidence_threshold", 0.5),
        target_classes=config.get("target_classes", [])
    )
    dispatcher = AlertDispatcher(config=config)

    src = config.get("camera_source", 0)
    print(f"\n[+] Connecting to camera sensor: {src}...")
    cap = cv2.VideoCapture(src)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    if not cap.isOpened():
        print(f"[!] Error: Could not open camera {src}. Exiting.")
        return

    print("\n=======================================================")
    print("  🛡️ SECURITY CAMERA DAEMON RUNNING")
    print(f"  Target Classes: {config.get('target_classes')}")
    print(f"  NTFY Push Alert: {'ENABLED' if config.get('ntfy_enabled') else 'DISABLED'} (Topic: {config.get('ntfy_topic')})")
    print(f"  Twilio SMS Alert: {'ENABLED' if config.get('twilio_enabled') else 'DISABLED'} (Phone: {config.get('target_phone_number')})")
    print("  Controls in window: [Q] Quit | [S] Snap | [Z] Toggle Zone")
    print("=======================================================\n")

    zone = config.get("security_zone")
    prev_time = time.time()
    alert_banner_until = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.05)
            continue

        detections = detector.detect(frame)
        now = time.time()
        fps = int(1.0 / (now - prev_time + 1e-6))
        prev_time = now

        # Check if alert condition is met
        should_alert = False
        if detections:
            if zone:
                # Alert only on zone intrusion
                for det in detections:
                    if detector.check_intrusion(det, zone):
                        should_alert = True
                        break
            else:
                # Alert on any whitelisted detection
                should_alert = True

        # Trigger alert dispatch if condition holds
        if should_alert and dispatcher.can_alert():
            snap_path = None
            if config.get("save_local_snapshots", True):
                snap_path = detector.save_annotated_snapshot(frame, detections)

            dispatched = dispatcher.send_alert_async(
                detected_objects=detections,
                image_path=snap_path,
                zone_name="Restricted Area" if zone else "Camera Field"
            )
            if dispatched:
                alert_banner_until = time.time() + 3.0

        # Render display
        if not config.get("headless_mode", False):
            is_alerting = (time.time() < alert_banner_until)
            hud_frame = detector.draw_hud(frame, detections, fps=fps, zone=zone, is_alert=is_alerting)
            cv2.imshow("Security Cam Monitor - Live Feed", hud_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break
            elif key == ord('s'):
                detector.save_annotated_snapshot(frame, detections)
                print("[+] Manual snapshot saved.")
            elif key == ord('z'):
                if zone is None:
                    h, w = frame.shape[:2]
                    zone = [int(w * 0.25), int(h * 0.25), int(w * 0.75), int(h * 0.75)]
                    print(f"[+] Security zone armed: {zone}")
                else:
                    zone = None
                    print("[-] Security zone cleared.")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
